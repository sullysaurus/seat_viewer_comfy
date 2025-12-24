#!/usr/bin/env python3
"""
View From Seat - Generate photorealistic venue views

CLI tool to generate prompts and select reference images for
seat-specific venue view generation.

Usage:
    python main.py --venue red_rocks --row 35
    python main.py --venue red_rocks --row 10 --section RESERVED
    python main.py --venue red_rocks --row 50 --angle -30
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.venue import load_venue, list_venues
from src.position import get_seat_position, list_available_rows
from src.reference import select_references, format_reference_selection
from src.prompt import build_prompt, build_negative_prompt, format_prompt_output


def main():
    parser = argparse.ArgumentParser(
        description="Generate view-from-seat prompts and reference selections"
    )
    parser.add_argument(
        "--venue", "-v",
        type=str,
        default="red_rocks",
        help="Venue ID (default: red_rocks)"
    )
    parser.add_argument(
        "--row", "-r",
        type=int,
        required=True,
        help="Row number"
    )
    parser.add_argument(
        "--section", "-s",
        type=str,
        default="RESERVED",
        help="Section name (default: RESERVED)"
    )
    parser.add_argument(
        "--angle", "-a",
        type=float,
        default=None,
        help="Override angle (degrees, -45 to +45). If not set, calculated from coordinates."
    )
    parser.add_argument(
        "--refs", "-n",
        type=int,
        default=1,
        help="Number of reference images to select (default: 1)"
    )
    parser.add_argument(
        "--list-rows",
        action="store_true",
        help="List available rows for the venue"
    )
    parser.add_argument(
        "--list-venues",
        action="store_true",
        help="List available venues"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--copy-prompt",
        action="store_true",
        help="Copy positive prompt to clipboard (macOS only)"
    )
    parser.add_argument(
        "--output", "-o",
        action="store_true",
        help="Save output to outputs/ directory as JSON"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent

    # Handle list commands
    if args.list_venues:
        venues = list_venues(project_root / "config" / "venues")
        print("Available venues:")
        for v in venues:
            print(f"  - {v}")
        return

    # Load venue config
    try:
        venue = load_venue(args.venue, project_root / "config" / "venues")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Available venues: {list_venues(project_root / 'config' / 'venues')}")
        sys.exit(1)

    csv_path = project_root / venue.csv_path

    # Handle list rows
    if args.list_rows:
        rows = list_available_rows(csv_path, args.section)
        print(f"Available rows in {args.section}:")
        print(f"  Rows {min(rows)} - {max(rows)} ({len(rows)} total)")
        return

    # Get seat position
    position = get_seat_position(
        csv_path=csv_path,
        stage_x=venue.stage_position["x"],
        stage_y=venue.stage_position["y"],
        section=args.section,
        row=args.row,
        row_range=venue.row_range
    )

    if position is None:
        print(f"Error: Row {args.row} not found in section {args.section}")
        available = list_available_rows(csv_path, args.section)
        if available:
            print(f"Available rows: {min(available)} - {max(available)}")
        sys.exit(1)

    # Override angle if specified
    if args.angle is not None:
        position.angle = args.angle
        # Recalculate angle type
        if args.angle < -15:
            position.angle_type = "left"
        elif args.angle > 15:
            position.angle_type = "right"
        else:
            position.angle_type = "center"

    # Select reference images
    references = select_references(
        position,
        venue.reference_images,
        max_results=args.refs,
        project_root=project_root
    )

    # Build prompts
    positive_prompt = build_prompt(position, venue)
    negative_prompt = build_negative_prompt(venue)

    # Build output data structure
    output_data = {
        "venue": venue.id,
        "position": {
            "section": position.section,
            "row": position.row,
            "x": position.x,
            "y": position.y,
            "angle": position.angle,
            "distance_type": position.distance_type,
            "angle_type": position.angle_type
        },
        "references": [
            {
                "path": ref.path,
                "depth_path": ref.depth_path,
                "row": ref.row,
                "angle": ref.angle,
                "distance_score": ref.distance
            }
            for ref in references
        ],
        "prompts": {
            "positive": positive_prompt,
            "negative": negative_prompt
        }
    }

    # Save to file if requested
    if args.output:
        outputs_dir = project_root / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{venue.id}_{position.section}_row{position.row}_{timestamp}.json"
        output_path = outputs_dir / filename
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"[Saved to {output_path}]")

    # Output
    if args.json:
        print(json.dumps(output_data, indent=2))
    else:
        print("\n" + "=" * 60)
        print(f"VIEW FROM SEAT: {venue.name}")
        print("=" * 60)

        print(f"\nPosition: {position.section} Row {position.row}")
        print(f"Coordinates: X={position.x:.1f}, Y={position.y:.1f}")
        print(f"Calculated angle: {position.angle:.1f}°")
        print(f"View type: {position.distance_type} / {position.angle_type}")

        print("\n" + "-" * 60)
        print(format_reference_selection(references))

        print("\n" + "-" * 60)
        print(format_prompt_output(positive_prompt, negative_prompt))

        print("\n" + "=" * 60)
        print("NEXT STEPS (ControlNet workflow):")
        print("1. Open ComfyUI")
        print("2. Import workflow: workflows/view_from_seat_controlnet.json")
        print("3. Upload STYLE reference:", references[0].path if references else "N/A")
        print("4. Upload DEPTH map:", references[0].depth_path if references else "N/A")
        print("5. Paste the positive prompt above")
        print("6. Run generation!")
        print("=" * 60)

    # Copy to clipboard (macOS)
    if args.copy_prompt:
        try:
            import subprocess
            subprocess.run(
                ["pbcopy"],
                input=positive_prompt.encode(),
                check=True
            )
            print("\n[Positive prompt copied to clipboard!]")
        except Exception as e:
            print(f"\n[Could not copy to clipboard: {e}]")


if __name__ == "__main__":
    main()
