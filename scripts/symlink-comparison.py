#!/usr/bin/env python3
"""
Usage: ./symlink-comparison.py /path/to/state1.json /path/to/state2.json [/path/to/output_report.json]

This script works with the JSON files produced by state-capture.py.
"""

import os
import sys
import json
import re
import datetime
import time
from collections import defaultdict


def load_json_file(filepath):
    """Load and parse a JSON file."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        sys.exit(1)


def normalize_path(path):
    """
    Normalize a path by replacing Nix store hash with "HASH".
    e.g. nix/store/abc123-system-path/bin/ls -> nix/store/HASH-system-path/bin/ls
    works on nix/.ro-store and nix/.rw-store as well.
    """
    # Handle paths with or without leading slash
    path = path.lstrip("/")

    # Match Nix store paths with their hash components
    pattern = r"(nix/(?:\.r[wo]-)?store/)[a-z0-9]{32}-(.+)"
    return re.sub(pattern, r"\1HASH-\2", path)


def fix_path(path):
    return path.lstrip("/")


def build_normalized_path_index(paths):
    """
    Build an index mapping normalized paths to actual paths.
    Should make lookup be O(1)
    """
    index = defaultdict(list)
    for path in paths:
        norm_path = normalize_path(path)
        index[norm_path].append(path)
    return index


def resolve_symlink_chain(path, symlinks, files, cache=None, max_depth=20):
    """
    Follow a symlink chain until reaching a regular file or a broken link.
    Returns a tuple of (final_path, is_broken, file_hash, status).
    """
    if cache is None:
        cache = {}

    # Check if we've already resolved this path
    if path in cache:
        return cache[path]

    # Initialize variables for traversal
    visited = set()
    current_path = path
    depth = 0

    while depth < max_depth:
        # Detect cycles
        if current_path in visited:
            result = (current_path, True, None, "cycle")
            cache[path] = result
            return result

        visited.add(current_path)
        depth += 1

        # If current path isn't a symlink, we've reached the end
        if current_path not in symlinks:
            # Clean path for lookup in files
            clean_path = fix_path(current_path)
            if clean_path in files and files[clean_path].get("hash") is not None:
                result = (current_path, False, files[clean_path]["hash"], "file")
                cache[path] = result
                return result
            result = (current_path, True, None, "missing")
            cache[path] = result
            return result

        # Get symlink target
        target = symlinks[current_path].get("target")

        # Handle broken links
        if not target:
            result = (current_path, True, None, "broken")
            cache[path] = result
            return result

        # Handle relative symlinks
        if not target.startswith("/"):
            base_dir = os.path.dirname(current_path)
            target = os.path.normpath(os.path.join(base_dir, target))
        else:
            # Remove leading slash for consistency with data format
            target = target.lstrip("/")

        # Continue following the chain
        current_path = target

    # If we reach here, we hit the max depth
    result = (current_path, True, None, "max_depth")
    cache[path] = result
    return result


def analyze_symlink_structure(state1, state2):
    """Analyze the structure of symlinks to understand patterns."""
    symlinks1 = state1.get("symlinks", {})
    symlinks2 = state2.get("symlinks", {})

    # Count paths with specific patterns
    nix_store_count1 = sum(1 for path in symlinks1 if "nix/store/" in path)
    nix_store_count2 = sum(1 for path in symlinks2 if "nix/store/" in path)

    ro_store_count1 = sum(1 for path in symlinks1 if "nix/.ro-store/" in path)
    ro_store_count2 = sum(1 for path in symlinks2 if "nix/.ro-store/" in path)

    rw_store_count1 = sum(1 for path in symlinks1 if "nix/.rw-store/" in path)
    rw_store_count2 = sum(1 for path in symlinks2 if "nix/.rw-store/" in path)

    print("\nSymlink Structure Analysis:")
    print(
        f"  Paths with nix/store/: {nix_store_count1} in state1, {nix_store_count2} in state2"
    )
    print(
        f"  Paths with nix/.ro-store/: {ro_store_count1} in state1, {ro_store_count2} in state2"
    )
    print(
        f"  Paths with nix/.rw-store/: {rw_store_count1} in state1, {rw_store_count2} in state2"
    )

    # Check a sample of paths for store hash patterns
    sample_paths = list(symlinks1.keys())[:10]
    print("\nSample path analysis:")
    for path in sample_paths:
        target = symlinks1[path].get("target", "None")
        print(f"  Path: {path} -> {target}")
        hash_match = re.search(r"nix/(?:\.r[wo]-)?store/([a-z0-9]{32})-", path)
        print(f"    Hash: {hash_match.group(1) if hash_match else 'no match'}")

    # Check sample resolution
    print("\nSample symlink resolution:")
    resolve_cache = {}
    for path in sample_paths[:3]:
        final_path, is_broken, file_hash, status = resolve_symlink_chain(
            path, symlinks1, state1.get("files", {}), resolve_cache
        )
        print(f"  {path} -> {final_path} (broken: {is_broken}, status: {status})")


def find_equivalent_symlinks(state1, state2, batch_size=5000):
    """
    Identify symlinks in both states that are equivalent.
    """
    symlinks1 = state1.get("symlinks", {})
    symlinks2 = state2.get("symlinks", {})
    files1 = state1.get("files", {})
    files2 = state2.get("files", {})

    # Get all paths from both states
    all_paths1 = set(list(symlinks1.keys()) + list(files1.keys()))
    all_paths2 = set(list(symlinks2.keys()) + list(files2.keys()))

    # Build normalized path indices for faster lookups
    print("Building path indices...")
    path_index2 = build_normalized_path_index(all_paths2)

    # Results storage
    results = {
        "matching_paths": [],  # Symlinks with matching normalized paths
        "different_targets": [],  # Matching paths with different direct targets
        "identical_final_content": [],  # Different paths but identical final content
        "different_final_content": [],  # Different paths with different final content
        "broken_in_both": [],  # Broken in both states
        "broken_only_in_state1": [],  # Broken only in state 1
        "broken_only_in_state2": [],  # Broken only in state 2
        "stats": {
            "total_symlinks_state1": len(symlinks1),
            "total_symlinks_state2": len(symlinks2),
            "matching_paths": 0,
            "different_targets": 0,
            "identical_final_content": 0,
            "different_final_content": 0,
            "broken_in_both": 0,
            "broken_only_in_state1": 0,
            "broken_only_in_state2": 0,
            "store_path_mappings": {},  # Will store mappings between store paths
        },
    }

    # Store path mappings (for analysis)
    store_path_mappings = {}

    # Resolution caches to avoid redoing work
    resolve_cache1 = {}
    resolve_cache2 = {}

    # Process symlinks from state1 in batches
    symlinks1_list = list(symlinks1.keys())
    total_batches = (len(symlinks1_list) + batch_size - 1) // batch_size

    print(f"Processing {len(symlinks1_list)} symlinks in {total_batches} batches...")

    for batch_num, start_idx in enumerate(range(0, len(symlinks1_list), batch_size)):
        batch = symlinks1_list[start_idx : start_idx + batch_size]

        for path1 in batch:
            # Normalize the path
            norm_path = normalize_path(path1)

            # Find matching paths in state2 using the index
            paths2 = path_index2.get(norm_path, [])

            # Filter to just symlinks
            paths2 = [p for p in paths2 if p in symlinks2]

            if paths2:  # If matching symlinks found in state2
                path2 = paths2[0]  # Take the first match
                target1 = symlinks1[path1].get("target")
                target2 = symlinks2[path2].get("target")

                # Record match
                path_match = {
                    "state1_path": path1,
                    "state2_path": path2,
                    "state1_target": target1,
                    "state2_target": target2,
                }
                results["matching_paths"].append(path_match)
                results["stats"]["matching_paths"] += 1

                # Extract store paths for mapping
                store_match1 = re.search(
                    r"(nix/(?:\.r[wo]-)?store/[a-z0-9]{32}-[^/]+)", path1
                )
                store_match2 = re.search(
                    r"(nix/(?:\.r[wo]-)?store/[a-z0-9]{32}-[^/]+)", path2
                )

                if store_match1 and store_match2:
                    store_path1 = store_match1.group(1)
                    store_path2 = store_match2.group(1)

                    # Record this mapping
                    if store_path1 not in store_path_mappings:
                        store_path_mappings[store_path1] = store_path2

                # Check if direct targets are different
                if normalize_path(target1 or "") != normalize_path(target2 or ""):
                    results["different_targets"].append(path_match)
                    results["stats"]["different_targets"] += 1

                # Resolve symlink chains in both states
                final_path1, broken1, hash1, status1 = resolve_symlink_chain(
                    path1, symlinks1, files1, resolve_cache1
                )
                final_path2, broken2, hash2, status2 = resolve_symlink_chain(
                    path2, symlinks2, files2, resolve_cache2
                )

                # Update path match with resolved information
                path_match.update(
                    {
                        "state1_final_path": final_path1,
                        "state2_final_path": final_path2,
                        "state1_broken": broken1,
                        "state2_broken": broken2,
                        "state1_final_hash": hash1,
                        "state2_final_hash": hash2,
                        "state1_status": status1,
                        "state2_status": status2,
                    }
                )

                # Check for broken links
                if broken1 and broken2:
                    results["broken_in_both"].append(path_match)
                    results["stats"]["broken_in_both"] += 1
                elif broken1:
                    results["broken_only_in_state1"].append(path_match)
                    results["stats"]["broken_only_in_state1"] += 1
                elif broken2:
                    results["broken_only_in_state2"].append(path_match)
                    results["stats"]["broken_only_in_state2"] += 1
                # Check if final content is identical
                elif hash1 == hash2:
                    results["identical_final_content"].append(path_match)
                    results["stats"]["identical_final_content"] += 1
                else:
                    results["different_final_content"].append(path_match)
                    results["stats"]["different_final_content"] += 1

    # Add store path mappings to stats
    results["stats"]["store_path_mappings"] = store_path_mappings

    return results


def analyze_store_paths(symlink_results):
    """Analyze the patterns in Nix store paths that are equivalent between states."""
    print("Analyzing store path patterns...")
    store_path_mappings = symlink_results["stats"]["store_path_mappings"]

    # Extract package names and analyze patterns
    package_mappings = {}
    for path1, path2 in store_path_mappings.items():
        # Extract the package name from the path
        match1 = re.search(r"nix/(?:\.r[wo]-)?store/[a-z0-9]{32}-([^/]+)", path1)
        match2 = re.search(r"nix/(?:\.r[wo]-)?store/[a-z0-9]{32}-([^/]+)", path2)

        if match1 and match2:
            package1 = match1.group(1)
            package2 = match2.group(1)

            if package1 not in package_mappings:
                package_mappings[package1] = set()

            package_mappings[package1].add(package2)

    # Analyze consistency
    consistent_mappings = {}
    inconsistent_mappings = {}

    for pkg1, pkg2_set in package_mappings.items():
        if len(pkg2_set) == 1:
            consistent_mappings[pkg1] = next(iter(pkg2_set))
        else:
            inconsistent_mappings[pkg1] = list(pkg2_set)

    return {
        "consistent_package_mappings": consistent_mappings,
        "inconsistent_package_mappings": inconsistent_mappings,
        "total_store_paths": len(store_path_mappings),
        "unique_packages_state1": len(package_mappings),
        "consistent_mappings_count": len(consistent_mappings),
        "inconsistent_mappings_count": len(inconsistent_mappings),
    }


def generate_report(state1_path, state2_path, symlink_results, store_analysis):
    """Generate a report of the symlink comparison."""
    report = {
        "summary": {
            "state1_path": state1_path,
            "state2_path": state2_path,
            "analysis_time": datetime.datetime.now().isoformat(),
            "total_symlinks_state1": symlink_results["stats"]["total_symlinks_state1"],
            "total_symlinks_state2": symlink_results["stats"]["total_symlinks_state2"],
            "matching_paths": symlink_results["stats"]["matching_paths"],
            "identical_final_content": symlink_results["stats"][
                "identical_final_content"
            ],
            "different_final_content": symlink_results["stats"][
                "different_final_content"
            ],
            "broken_links": {
                "in_both_states": symlink_results["stats"]["broken_in_both"],
                "only_in_state1": symlink_results["stats"]["broken_only_in_state1"],
                "only_in_state2": symlink_results["stats"]["broken_only_in_state2"],
            },
            "store_path_analysis": {
                "total_mapped_paths": store_analysis["total_store_paths"],
                "unique_packages": store_analysis["unique_packages_state1"],
                "consistent_mappings": store_analysis["consistent_mappings_count"],
                "inconsistent_mappings": store_analysis["inconsistent_mappings_count"],
            },
        },
        "symlink_analysis": {
            "identical_final_content": symlink_results["identical_final_content"][
                :100
            ],  # Limit to 100 examples
            "different_final_content": symlink_results["different_final_content"][:100],
            "broken_in_both": symlink_results["broken_in_both"][:50],
            "broken_only_in_state1": symlink_results["broken_only_in_state1"][:50],
            "broken_only_in_state2": symlink_results["broken_only_in_state2"][:50],
        },
        "store_path_analysis": {
            "consistent_package_mappings": store_analysis[
                "consistent_package_mappings"
            ],
            "inconsistent_package_mappings": store_analysis[
                "inconsistent_package_mappings"
            ],
        },
    }

    return report


def main():
    """Main function."""
    if len(sys.argv) < 3:
        print(
            f"Usage: {sys.argv[0]} /path/to/state1.json /path/to/state2.json [/path/to/output_report.json]"
        )
        sys.exit(1)

    state1_path = sys.argv[1]
    state2_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    start_time = time.time()
    print(f"Analyzing symlinks between NixOS states...")
    print(f"State 1: {state1_path}")
    print(f"State 2: {state2_path}")

    print("Loading state files...")
    state1 = load_json_file(state1_path)
    state2 = load_json_file(state2_path)

    # First, analyze the structure of symlinks to understand the data
    analyze_symlink_structure(state1, state2)

    print("Identifying equivalent symlinks...")
    symlink_results = find_equivalent_symlinks(state1, state2)

    print("Analyzing Nix store path patterns...")
    store_analysis = analyze_store_paths(symlink_results)

    print("Generating report...")
    report = generate_report(state1_path, state2_path, symlink_results, store_analysis)

    if output_path:
        try:
            print(f"Saving report to {output_path}...")
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Report saved successfully.")
        except Exception as e:
            print(f"Error saving report: {e}")

    elapsed_time = time.time() - start_time
    print(f"\nTotal analysis time: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
