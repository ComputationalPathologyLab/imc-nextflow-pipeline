from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import tifffile as tiff


TIFF_SUFFIXES = (".ome.tiff", ".ome.tif", ".tiff", ".tif")


def strip_tiff_suffix(name: str) -> str:
    lower = name.lower()
    for suffix in TIFF_SUFFIXES:
        if lower.endswith(suffix):
            return name[: -len(suffix)]
    return Path(name).stem


def parse_channel_file(path: Path):
    base = strip_tiff_suffix(path.name)
    if "_" in base:
        channel, marker = base.split("_", 1)
    else:
        channel, marker = base, base
    return channel, marker


def channel_sort_key(path: Path):
    channel, marker = parse_channel_file(path)
    match = re.match(r"^(\d+)([A-Za-z].*)?$", channel)
    if match:
        mass = int(match.group(1))
        tail = match.group(2) or ""
    else:
        mass = 10**9
        tail = channel
    return mass, tail, marker


def list_tiff_files(folder: Path):
    files = [
        p for p in folder.iterdir()
        if p.is_file() and p.name.lower().endswith((".tif", ".tiff"))
    ]
    return sorted(files, key=channel_sort_key)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python stack_one_roi.py <roi_dir> <output_tiff>")

    roi_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    if not roi_dir.exists():
        raise FileNotFoundError(f"ROI directory does not exist: {roi_dir}")

    files = list_tiff_files(roi_dir)
    if not files:
        raise FileNotFoundError(f"No TIFF files found in: {roi_dir}")

    imgs = []
    shapes = []

    for f in files:
        img = tiff.imread(f)
        if img.ndim != 2:
            raise ValueError(f"{f.name} is not 2D. Shape: {img.shape}")
        imgs.append(img)
        shapes.append(img.shape)

    if len(set(shapes)) != 1:
        raise ValueError(f"Channel shapes do not match: {set(shapes)}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    stack = np.stack(imgs, axis=0)
    tiff.imwrite(out_path, stack)

    print(f"Wrote {out_path}")
    print(f"Shape: {stack.shape}")


if __name__ == "__main__":
    main()