#!/usr/bin/env python3
"""
Usage: ./state-capture.py /path/to/root /path/to/output.json
"""

import os
import sys
import json
import hashlib
import time
import datetime


def get_symlink_target(filepath):
    """Get the target of a symlink."""
    try:
        return os.readlink(filepath)
    except Exception as e:
        print(f"Error reading symlink {filepath}: {e}")
        return None


def calculate_hash(filepath):
    """Calculate SHA256 hash of a file's contents."""
    try:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            buf = f.read(65536)  # Read in 64k chunks
            while buf:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError, IsADirectoryError):
        return None
    except Exception as e:
        print(f"Error hashing {filepath}: {e}")
        return None


def get_file_metadata(filepath):
    """Get file metadata."""
    try:
        stat = os.stat(filepath)
        return {
            "size": stat.st_size,
            "mode": stat.st_mode,
            "uid": stat.st_uid,
            "gid": stat.st_gid,
            "mtime": stat.st_mtime,
        }
    except (PermissionError, FileNotFoundError):
        return None


def scan_directory(directory):
    """Scan a directory and return file hashes, metadata, symlink info."""
    file_data = {}
    symlink_data = {}

    # to be skipped
    skip_dirs = ["/proc", "/sys", "/dev", "/run"]

    print(f"Scanning {directory}...")
    file_count = 0
    symlink_count = 0

    for root, dirs, files in os.walk(directory):
        # Skip excluded paths
        dirs[:] = [d for d in dirs if os.path.join(root, d) not in skip_dirs]

        for filename in files:
            filepath = os.path.join(root, filename)
            relpath = os.path.relpath(filepath, directory)

            if os.path.islink(filepath):
                # symlink
                target = get_symlink_target(filepath)
                symlink_data[relpath] = {
                    "target": target,
                    "metadata": get_file_metadata(filepath),
                }
            else:
                # normal file
                try:
                    metadata = get_file_metadata(filepath)
                    if metadata:
                        hash_value = calculate_hash(filepath)
                        file_data[relpath] = {"hash": hash_value, "metadata": metadata}
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

    return {"files": file_data, "symlinks": symlink_data}


def capture_system_info():
    """Capture basic system information."""
    system_info = {}

    # Get hostname
    try:
        system_info["hostname"] = os.uname().nodename
    except:
        system_info["hostname"] = "unknown"

    # Get kernel version
    try:
        system_info["kernel"] = os.uname().release
    except:
        system_info["kernel"] = "unknown"

    # get machine ID
    if os.path.exists("/etc/machine-id"):
        try:
            with open("/etc/machine-id", "r") as f:
                system_info["machine_id"] = f.read().strip()
        except:
            system_info["machine_id"] = "unknown"

    # get timestamp
    system_info["capture_time"] = datetime.datetime.now().isoformat()

    return system_info


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} /path/to/directory /path/to/output.json")
        sys.exit(1)

    directory_path = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.isdir(directory_path):
        print(f"Error: {directory_path} is not a directory")
        sys.exit(1)

    start_time = time.time()

    print(f"Starting filesystem scan of {directory_path}")
    scan_results = scan_directory(directory_path)
    system_info = capture_system_info()

    # Combine all data
    result = {
        "system_info": system_info,
        "files": scan_results["files"],
        "symlinks": scan_results["symlinks"],
    }

    # Save to file
    with open(output_file, "w") as f:
        json.dump(result, f)

    elapsed_time = time.time() - start_time
    print(f"Scan completed in {elapsed_time:.2f} seconds")
    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()
