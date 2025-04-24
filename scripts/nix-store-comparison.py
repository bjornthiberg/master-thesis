#!/usr/bin/env python3
"""
Usage: ./compare-store-paths.py state1.json state2.json [output.json]

This script works with the JSON files produced by state-capture.py.

Only looks at nix/store, not nix/.ro-store or nix/.rw-store
"""

import sys
import json
import re
from collections import defaultdict
from pathlib import Path


def load_state_file(path):
    with open(path, "r") as f:
        return json.load(f)


def normalize_store_path(path):
    # nix/store/<hash>-name/path/to/file -> nix/store/HASH-name/path/to/file
    return re.sub(r"(nix/store/)[a-z0-9]{32}-", r"\1HASH-", path)


def build_index(files_dict):
    """
    Build mapping of normalized nix store paths to their full path and hash.
    """
    index = defaultdict(list)
    for path, info in files_dict.items():
        if path.startswith("nix/store/") and info.get("hash"):
            norm = normalize_store_path(path)
            index[norm].append((path, info["hash"]))
    return index


def compare_indexes(index1, index2):
    all_keys = set(index1.keys()) | set(index2.keys())
    results = {
        "identical": [],
        "differing": [],
        "only_in_state1": [],
        "only_in_state2": [],
    }

    for key in sorted(all_keys):
        entries1 = index1.get(key, [])
        entries2 = index2.get(key, [])

        if entries1 and entries2:
            # Check if any hashes match across the two
            hashes1 = {h for _, h in entries1}
            hashes2 = {h for _, h in entries2}

            if hashes1 & hashes2:
                results["identical"].append(
                    {"normalized_path": key, "state1": entries1, "state2": entries2}
                )
            else:
                results["differing"].append(
                    {"normalized_path": key, "state1": entries1, "state2": entries2}
                )
        elif entries1:
            results["only_in_state1"].append(
                {"normalized_path": key, "state1": entries1}
            )
        elif entries2:
            results["only_in_state2"].append(
                {"normalized_path": key, "state2": entries2}
            )

    return results


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} state1.json state2.json [output.json]")
        sys.exit(1)

    state1_path = sys.argv[1]
    state2_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    print("Loading state files...")
    state1 = load_state_file(state1_path)
    state2 = load_state_file(state2_path)

    print("Indexing nix store paths...")
    index1 = build_index(state1.get("files", {}))
    index2 = build_index(state2.get("files", {}))

    print("Comparing normalized paths...")
    diff = compare_indexes(index1, index2)

    print("\n=== Summary ===")
    print(f"Identical content: {len(diff['identical'])}")
    print(f"Different content: {len(diff['differing'])}")
    print(f"Only in state 1: {len(diff['only_in_state1'])}")
    print(f"Only in state 2: {len(diff['only_in_state2'])}")

    if output_path:
        with open(output_path, "w") as f:
            json.dump(diff, f, indent=2)
        print(f"\nDetailed diff written to {output_path}")


if __name__ == "__main__":
    main()
