"""
Reference image selection.
Selects the best reference images based on target seat position.
"""

import math
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

from .position import SeatPosition


@dataclass
class ReferenceMatch:
    """A reference image with its match score."""
    path: str
    row: int
    angle: float
    distance: float  # Combined distance score (lower is better)
    description: str
    depth_path: str = ""  # Path to corresponding depth map


def calculate_distance(
    target_row: int,
    target_angle: float,
    ref_row: int,
    ref_angle: float,
    row_weight: float = 2.0,
    angle_weight: float = 1.0
) -> float:
    """
    Calculate weighted distance between target position and reference position.

    Row differences are weighted more heavily because they have more visual impact
    (distance from stage, elevation) than horizontal angle differences.

    Args:
        target_row: Target row number
        target_angle: Target angle in degrees
        ref_row: Reference image row
        ref_angle: Reference image angle
        row_weight: Weight for row difference (default 2.0)
        angle_weight: Weight for angle difference (default 1.0)

    Returns:
        Combined weighted distance score (lower is better)
    """
    # Normalize row difference (rows typically 1-70, so divide by 70)
    row_diff = abs(target_row - ref_row) / 70.0

    # Normalize angle difference (angles typically -45 to +45, so divide by 90)
    angle_diff = abs(target_angle - ref_angle) / 90.0

    # Weighted Euclidean distance
    distance = math.sqrt(
        (row_weight * row_diff) ** 2 +
        (angle_weight * angle_diff) ** 2
    )

    return distance


def select_references(
    target_position: SeatPosition,
    reference_images: List[dict],
    max_results: int = 3,
    project_root: Optional[Path] = None
) -> List[ReferenceMatch]:
    """
    Select the best matching reference images for a target seat position.

    Args:
        target_position: The target seat position
        reference_images: List of reference image configs from venue YAML
        max_results: Maximum number of references to return (default 3)
        project_root: Optional project root path for resolving image paths

    Returns:
        List of ReferenceMatch objects, sorted by distance (best first)
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    matches = []

    for ref in reference_images:
        ref_row = ref["position"]["row"]
        ref_angle = ref["position"]["angle"]

        distance = calculate_distance(
            target_position.row,
            target_position.angle,
            ref_row,
            ref_angle
        )

        # Resolve path relative to project root
        path = str(project_root / ref["path"])

        # Compute depth map path (same name with _depth suffix in depth_maps folder)
        ref_path = Path(ref["path"])
        depth_filename = f"{ref_path.stem}_depth.png"
        depth_path = str(project_root / ref_path.parent / "depth_maps" / depth_filename)

        matches.append(ReferenceMatch(
            path=path,
            row=ref_row,
            angle=ref_angle,
            distance=distance,
            description=ref.get("description", ""),
            depth_path=depth_path
        ))

    # Sort by distance (best matches first)
    matches.sort(key=lambda m: m.distance)

    return matches[:max_results]


def get_best_reference(
    target_position: SeatPosition,
    reference_images: List[dict],
    project_root: Optional[Path] = None
) -> Optional[ReferenceMatch]:
    """
    Get the single best matching reference image.

    Args:
        target_position: The target seat position
        reference_images: List of reference image configs from venue YAML
        project_root: Optional project root path

    Returns:
        Best matching ReferenceMatch or None if no references available
    """
    matches = select_references(
        target_position,
        reference_images,
        max_results=1,
        project_root=project_root
    )
    return matches[0] if matches else None


def format_reference_selection(matches: List[ReferenceMatch]) -> str:
    """
    Format reference selection results for display.

    Args:
        matches: List of ReferenceMatch objects

    Returns:
        Formatted string describing the selections
    """
    if not matches:
        return "No reference images selected."

    lines = ["Selected reference images:"]
    for i, match in enumerate(matches, 1):
        lines.append(
            f"  {i}. {Path(match.path).name} "
            f"(row {match.row}, angle {match.angle}°, "
            f"score: {match.distance:.3f})"
        )
        if match.description:
            lines.append(f"     {match.description}")

    return "\n".join(lines)
