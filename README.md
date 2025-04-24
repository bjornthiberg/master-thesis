# Degree Project – Public Resources

This repository contains the public artifacts used for my master's thesis project.

The goal of the project was to deploy and evaluate two approaches for personalizing non-persistent NixOS systems—**pre-boot** (build-time integration) and **post-boot** (runtime application).

---

## Structure

```
degree-project-public/
├── nixos-configurations/
│   ├── base/                     # Base NixOS flake
│   ├── preboot-personalized/     # Pre-boot personalization flake
│   └── postboot-personalized/    # Post-boot personalization setup (separate flake and home.nix)
└── scripts/
    ├── state-capture.py          # Captures a full file system state
    ├── state-comparison.py       # Compares two captured states
    ├── symlink-comparison.py     # Compares symlink resolution across states
    ├── nix-store-comparison.py   # Compares normalized Nix store content
    └── baseline-exclusions.txt   # Patterns excluded by baseline definition
````

## Usage

Each configuration is defined using Nix Flakes and includes everything needed to build a bootable NixOS ISO image. It only requires a working Nix installation and running `nix build path:$PWD`in the directory containing the flake (e.g. `nixos-configurations/base/`).

The scripts/ directory contains Python scripts used to:
- Capture full file system state snapshots.
- Compare two snapshots at a high level.
- Compare symlinks in two snapshots.
- Compare Nix stores in two snapshots.

## State capture and comparison results

Due to large file sizes, the raw state capture outputs and the state comparison results are hoste separately on [mega.nz, accessible here](https://mega.nz/folder/s8YyXZBY#EwQGJrcQ5nPYZ8jkugyObw).



