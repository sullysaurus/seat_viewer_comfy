"""
Prompt generation.
Creates position-aware prompts for image generation.
"""

from typing import Optional
from .position import SeatPosition
from .venue import VenueConfig


def build_prompt(
    position: SeatPosition,
    venue: VenueConfig,
    include_technical: bool = True
) -> str:
    """
    Build a position-aware prompt for image generation.

    Args:
        position: The target seat position
        venue: The venue configuration
        include_technical: Whether to include technical photography terms

    Returns:
        Complete prompt string
    """
    parts = []

    # Start with base venue description
    parts.append(f"Photorealistic view from audience seating at {venue.name}")

    # Add position-specific descriptions
    distance_desc = venue.get_distance_description(position.distance_type)
    if distance_desc:
        parts.append(distance_desc)
    else:
        # Fallback descriptions
        if position.distance_type == "front":
            parts.append("close to stage, looking up at performers")
        elif position.distance_type == "middle":
            parts.append("mid-distance from stage, balanced view")
        else:
            parts.append("far from stage, elevated panoramic view")

    # Add angle description
    angle_desc = venue.get_angle_description(position.angle_type)
    if angle_desc:
        parts.append(angle_desc)
    else:
        # Fallback descriptions
        if position.angle_type == "left":
            parts.append("viewing from left side of venue")
        elif position.angle_type == "right":
            parts.append("viewing from right side of venue")
        else:
            parts.append("center view of stage")

    # Add venue-specific elements
    elements = venue.get_prompt_elements()
    if elements:
        parts.extend(elements)

    # Add technical photography terms
    if include_technical:
        parts.extend([
            "professional concert photography",
            "wide panoramic shot",
            "8k resolution",
            "highly detailed",
            "natural lighting"
        ])

    # Join with commas
    prompt = ", ".join(parts)

    return prompt


def build_negative_prompt(venue: VenueConfig) -> str:
    """
    Build negative prompt for image generation.

    Args:
        venue: The venue configuration

    Returns:
        Negative prompt string
    """
    base_negative = venue.get_negative_prompt()

    if base_negative:
        return base_negative

    # Default negative prompt
    return (
        "blurry, low quality, cartoon, illustration, painting, drawing, "
        "daytime harsh lighting, empty black sky, distorted, deformed, "
        "ugly, watermark, text, indoor venue, wrong architecture"
    )


def build_row_specific_prompt(
    row: int,
    venue: VenueConfig,
    angle: float = 0.0
) -> str:
    """
    Build a prompt specifically for a row number without full position calculation.
    Useful for quick prompt generation.

    Args:
        row: Row number
        venue: Venue configuration
        angle: Optional angle in degrees (default 0 = center)

    Returns:
        Complete prompt string
    """
    # Determine distance type from row
    min_row = venue.row_range.get("min", 1)
    max_row = venue.row_range.get("max", 70)
    total_rows = max_row - min_row
    position_pct = (row - min_row) / total_rows

    if position_pct < 0.3:
        distance_type = "front"
    elif position_pct < 0.65:
        distance_type = "middle"
    else:
        distance_type = "back"

    # Determine angle type
    if angle < -15:
        angle_type = "left"
    elif angle > 15:
        angle_type = "right"
    else:
        angle_type = "center"

    parts = []

    # Base description
    parts.append(f"Photorealistic view from row {row} at {venue.name}")

    # Distance description
    distance_desc = venue.get_distance_description(distance_type)
    if distance_desc:
        parts.append(distance_desc)

    # Angle description
    angle_desc = venue.get_angle_description(angle_type)
    if angle_desc:
        parts.append(angle_desc)

    # Venue elements
    parts.extend(venue.get_prompt_elements())

    # Technical terms
    parts.extend([
        "professional concert photography",
        "wide panoramic shot",
        "8k resolution",
        "highly detailed"
    ])

    return ", ".join(parts)


def format_prompt_output(
    positive: str,
    negative: str,
    position: Optional[SeatPosition] = None
) -> str:
    """
    Format prompts for display/copying.

    Args:
        positive: Positive prompt
        negative: Negative prompt
        position: Optional position info

    Returns:
        Formatted string for display
    """
    lines = []

    if position:
        lines.append("=" * 60)
        lines.append(f"View from: {position.section} Row {position.row}")
        lines.append(f"Position: {position.distance_type} / {position.angle_type}")
        lines.append(f"Calculated angle: {position.angle:.1f}°")
        lines.append("=" * 60)

    lines.append("\n[POSITIVE PROMPT]")
    lines.append("-" * 40)
    lines.append(positive)

    lines.append("\n[NEGATIVE PROMPT]")
    lines.append("-" * 40)
    lines.append(negative)

    return "\n".join(lines)
