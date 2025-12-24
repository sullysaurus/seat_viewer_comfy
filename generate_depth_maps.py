#!/usr/bin/env python3
"""
Generate depth maps from reference photos using Depth Anything model.
"""

import torch
from pathlib import Path
from PIL import Image
import numpy as np
from transformers import pipeline

def generate_depth_maps(input_dir: Path, output_dir: Path):
    """Generate depth maps for all images in input directory."""

    # Initialize depth estimation pipeline
    print("Loading Depth Anything model...")
    depth_estimator = pipeline(
        task="depth-estimation",
        model="depth-anything/Depth-Anything-V2-Small-hf",
        device="mps" if torch.backends.mps.is_available() else "cpu"
    )

    # Find all jpg images
    images = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.png"))

    print(f"Found {len(images)} images to process")

    output_dir.mkdir(parents=True, exist_ok=True)

    for img_path in images:
        print(f"Processing {img_path.name}...")

        # Load image
        image = Image.open(img_path)

        # Run depth estimation
        result = depth_estimator(image)
        depth_map = result["depth"]

        # Save depth map
        output_path = output_dir / f"{img_path.stem}_depth.png"
        depth_map.save(output_path)
        print(f"  Saved: {output_path.name}")

    print(f"\nDone! Generated {len(images)} depth maps in {output_dir}")


if __name__ == "__main__":
    project_root = Path(__file__).parent
    input_dir = project_root / "photos" / "red_rocks"
    output_dir = project_root / "photos" / "red_rocks" / "depth_maps"

    generate_depth_maps(input_dir, output_dir)
