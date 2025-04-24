#!/usr/bin/env python3
"""
Usage: ./state-comparison.py /path/to/state1.json /path/to/state2.json /path/to/output_report.json [--exclude /path/to/exclusions.txt]
"""

import sys
import json
import datetime
from collections import defaultdict


def load_json_file(filepath):
    """Load JSON file."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        sys.exit(1)


def load_exclusion_patterns(filepath):
    """Load excluded paths from file."""
    try:
        patterns = []
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Normalize pattern: ensure it starts with /
                    if not line.startswith("/"):
                        line = "/" + line
                    patterns.append(line)
        return patterns
    except Exception as e:
        print(f"Error loading exclusion patterns from {filepath}: {e}")
        print("Continuing without exclusions.")
        return []


def should_exclude(filepath, exclusion_patterns):
    """Check if a filepath matches any exclusion pattern."""
    # Ensure filepath starts with / for consistent matching
    if not filepath.startswith("/"):
        filepath = "/" + filepath

    for pattern in exclusion_patterns:
        # Remove commented
        pattern = pattern.split("#")[0].strip()
        if not pattern:
            continue

        # Ensure pattern starts with / for consistent matching
        if not pattern.startswith("/"):
            pattern = "/" + pattern

        # Direct file match
        if filepath == pattern:
            return True

        # In directory
        if pattern.endswith("/") and (
            filepath.startswith(pattern) or filepath + "/" == pattern
        ):
            return True

    return False


def compare_system_info(state1, state2):
    """Compare system information between two states."""
    info1 = state1["system_info"]
    info2 = state2["system_info"]

    differences = {}
    for key in set(info1.keys()) | set(info2.keys()):
        if key not in info1:
            differences[key] = {"only_in_state2": info2[key]}
        elif key not in info2:
            differences[key] = {"only_in_state1": info1[key]}
        elif info1[key] != info2[key]:
            differences[key] = {"state1": info1[key], "state2": info2[key]}

    return differences


def get_file_differences(state1, state2, exclusion_patterns=None):
    """Compare files between two states."""
    if exclusion_patterns is None:
        exclusion_patterns = []

    files1 = state1["files"]
    files2 = state2["files"]

    filtered_files1 = {
        k: v for k, v in files1.items() if not should_exclude(k, exclusion_patterns)
    }
    filtered_files2 = {
        k: v for k, v in files2.items() if not should_exclude(k, exclusion_patterns)
    }

    all_files = set(filtered_files1.keys()) | set(filtered_files2.keys())

    # Categorize differences
    only_in_state1 = []
    only_in_state2 = []
    different_hash = []
    different_metadata = []
    identical = []

    for filepath in all_files:
        if filepath not in files1:
            only_in_state2.append(filepath)
        elif filepath not in files2:
            only_in_state1.append(filepath)
        else:
            # File exists in both states
            file1 = files1[filepath]
            file2 = files2[filepath]

            if file1["hash"] != file2["hash"]:
                different_hash.append(filepath)
            elif file1["metadata"] != file2["metadata"]:
                different_metadata.append(filepath)
            else:
                identical.append(filepath)

    return {
        "only_in_state1": only_in_state1,
        "only_in_state2": only_in_state2,
        "different_hash": different_hash,
        "different_metadata": different_metadata,
        "identical": identical,
    }


def get_symlink_differences(state1, state2, exclusion_patterns=None):
    """Compare symlinks between two states."""
    if exclusion_patterns is None:
        exclusion_patterns = []

    # Check if symlinks key exists in both states
    if "symlinks" not in state1 or "symlinks" not in state2:
        # Handle cases where one file might not have symlink data
        symlinks1 = state1.get("symlinks", {})
        symlinks2 = state2.get("symlinks", {})
    else:
        symlinks1 = state1["symlinks"]
        symlinks2 = state2["symlinks"]

    # Filter out excluded symlinks
    filtered_symlinks1 = {
        k: v for k, v in symlinks1.items() if not should_exclude(k, exclusion_patterns)
    }
    filtered_symlinks2 = {
        k: v for k, v in symlinks2.items() if not should_exclude(k, exclusion_patterns)
    }

    all_symlinks = set(filtered_symlinks1.keys()) | set(filtered_symlinks2.keys())

    # Categorize differences
    only_in_state1 = []
    only_in_state1_details = {}  # New dict for state1-only symlinks
    only_in_state2 = []
    only_in_state2_details = {}  # New dict for state2-only symlinks
    different_target = []
    different_target_details = {}
    different_metadata = []
    identical = []

    for filepath in all_symlinks:
        if filepath not in filtered_symlinks1:
            only_in_state2.append(filepath)
            only_in_state2_details[filepath] = {
                "target": filtered_symlinks2[filepath]["target"]
            }
        elif filepath not in filtered_symlinks2:
            only_in_state1.append(filepath)
            only_in_state1_details[filepath] = {
                "target": filtered_symlinks1[filepath]["target"]
            }
        else:
            link1 = filtered_symlinks1[filepath]
            link2 = filtered_symlinks2[filepath]

            if link1["target"] != link2["target"]:
                different_target.append(filepath)
                different_target_details[filepath] = {
                    "state1_target": link1["target"],
                    "state2_target": link2["target"],
                }
            elif link1["metadata"] != link2["metadata"]:
                different_metadata.append(filepath)
            else:
                identical.append(filepath)

    return {
        "only_in_state1": only_in_state1,
        "only_in_state1_details": only_in_state1_details,
        "only_in_state2": only_in_state2,
        "only_in_state2_details": only_in_state2_details,
        "different_target": different_target,
        "different_target_details": different_target_details,
        "different_metadata": different_metadata,
        "identical": identical,
    }


def analyze_path_patterns(file_list):
    """Analyze paths to identify common directories."""
    dir_counts = defaultdict(int)

    for filepath in file_list:
        parts = filepath.split("/")
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i])
            if prefix:
                dir_counts[prefix] += 1

    # Find significant directories (containing more than 5 different files)
    significant_dirs = {
        dir_path: count for dir_path, count in dir_counts.items() if count > 0
    }

    # Sort by count descending
    sorted_dirs = sorted(significant_dirs.items(), key=lambda x: x[1], reverse=True)

    return sorted_dirs[:50]  # Return top 50 directories


def generate_report(state1_path, state2_path, system_diff, file_diff, symlink_diff):
    """Generate a report of the diffs."""
    total_files = (
        len(file_diff["identical"])
        + len(file_diff["different_hash"])
        + len(file_diff["different_metadata"])
        + len(file_diff["only_in_state1"])
        + len(file_diff["only_in_state2"])
    )

    identical_count = len(file_diff["identical"])
    changed_count = len(file_diff["different_hash"]) + len(
        file_diff["different_metadata"]
    )
    only1_count = len(file_diff["only_in_state1"])
    only2_count = len(file_diff["only_in_state2"])

    # Symlink stats
    total_symlinks = (
        len(symlink_diff["identical"])
        + len(symlink_diff["different_target"])
        + len(symlink_diff["different_metadata"])
        + len(symlink_diff["only_in_state1"])
        + len(symlink_diff["only_in_state2"])
    )
    identical_symlinks = len(symlink_diff["identical"])
    changed_symlinks = len(symlink_diff["different_target"]) + len(
        symlink_diff["different_metadata"]
    )
    only1_symlinks = len(symlink_diff["only_in_state1"])
    only2_symlinks = len(symlink_diff["only_in_state2"])

    report = {
        "summary": {
            "state1_path": state1_path,
            "state2_path": state2_path,
            "comparison_time": datetime.datetime.now().isoformat(),
            "total_files": total_files,
            "identical_files": identical_count,
            "identical_percentage": round(identical_count / total_files * 100, 2)
            if total_files > 0
            else 0,
            "changed_files": changed_count,
            "only_in_state1": only1_count,
            "only_in_state2": only2_count,
            "total_symlinks": total_symlinks,
            "identical_symlinks": identical_symlinks,
            "identical_symlinks_percentage": round(
                identical_symlinks / total_symlinks * 100, 2
            )
            if total_symlinks > 0
            else 0,
            "changed_symlinks": changed_symlinks,
            "symlinks_only_in_state1": only1_symlinks,
            "symlinks_only_in_state2": only2_symlinks,
        },
        "system_info_differences": system_diff,
        "file_differences": {
            "counts": {
                "only_in_state1": only1_count,
                "only_in_state2": only2_count,
                "different_hash": len(file_diff["different_hash"]),
                "different_metadata": len(file_diff["different_metadata"]),
                "identical": identical_count,
            },
            "common_paths_only_in_state1": analyze_path_patterns(
                file_diff["only_in_state1"]
            ),
            "common_paths_only_in_state2": analyze_path_patterns(
                file_diff["only_in_state2"]
            ),
            "common_paths_different_hash": analyze_path_patterns(
                file_diff["different_hash"]
            ),
            "files_only_in_state1": file_diff["only_in_state1"][
                :200
            ],  # Limit to 100 examples
            "files_only_in_state2": file_diff["only_in_state2"][:200],
            "files_with_different_hash": file_diff["different_hash"][:200],
            "files_with_different_metadata": file_diff["different_metadata"][:10],
        },
        "symlink_differences": {
            "counts": {
                "only_in_state1": only1_symlinks,
                "only_in_state2": only2_symlinks,
                "different_target": len(symlink_diff["different_target"]),
                "different_metadata": len(symlink_diff["different_metadata"]),
                "identical": identical_symlinks,
            },
            "common_paths_only_in_state1": analyze_path_patterns(
                symlink_diff["only_in_state1"]
            ),
            "common_paths_only_in_state2": analyze_path_patterns(
                symlink_diff["only_in_state2"]
            ),
            "common_paths_different_target": analyze_path_patterns(
                symlink_diff["different_target"]
            ),
            "symlinks_only_in_state1": symlink_diff["only_in_state1"][:100],
            "symlinks_only_in_state1_details": symlink_diff["only_in_state1_details"],
            "symlinks_only_in_state2": symlink_diff["only_in_state2"][:100],
            "symlinks_only_in_state2_details": symlink_diff["only_in_state2_details"],
            "symlinks_with_different_target": symlink_diff["different_target"][:100],
            "symlinks_with_different_metadata": symlink_diff["different_metadata"][:10],
            "target_differences": symlink_diff["different_target_details"],
        },
    }

    return report


def main():
    """Main function."""
    # Updated usage message
    usage_msg = f"Usage: {sys.argv[0]} /path/to/state1.json /path/to/state2.json [/path/to/output_report.json] [--exclude /path/to/exclusions.txt]"

    if len(sys.argv) < 3:
        print(usage_msg)
        sys.exit(1)

    state1_path = sys.argv[1]
    state2_path = sys.argv[2]

    # Parse remaining args
    output_path = None
    exclusion_file = None

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--exclude" and i + 1 < len(sys.argv):
            exclusion_file = sys.argv[i + 1]
            i += 2
        elif i < len(sys.argv):
            output_path = sys.argv[i]
            i += 1
        else:
            i += 1

    # Load exclusion patterns if specified
    exclusion_patterns = []
    if exclusion_file:
        print(f"Loading exclusion patterns from {exclusion_file}")
        exclusion_patterns = load_exclusion_patterns(exclusion_file)
        print(f"Loaded {len(exclusion_patterns)} exclusion patterns")

    print(f"Comparing filesystem states...")
    print(f"State 1: {state1_path}")
    print(f"State 2: {state2_path}")

    global state1, state2
    state1 = load_json_file(state1_path)
    state2 = load_json_file(state2_path)

    system_diff = compare_system_info(state1, state2)
    file_diff = get_file_differences(state1, state2, exclusion_patterns)
    symlink_diff = get_symlink_differences(state1, state2, exclusion_patterns)

    report = generate_report(
        state1_path, state2_path, system_diff, file_diff, symlink_diff
    )

    if output_path:
        try:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\nDetailed report saved to: {output_path}")
        except Exception as e:
            print(f"Error saving report: {e}")


if __name__ == "__main__":
    main()
