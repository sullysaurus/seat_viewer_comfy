"""
Position and coordinate handling.
Parses CSV coordinates and calculates camera positions for seats.
"""

import csv
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class SeatPosition:
    """Represents a seat's position and viewing characteristics."""
    section: str
    row: int
    x: float
    y: float
    angle: float  # Degrees from center (-45 to +45)
    distance_type: str  # "front", "middle", or "back"
    angle_type: str  # "left", "center", or "right"


class CoordinateSystem:
    """Handles coordinate loading and position calculations."""

    def __init__(self, csv_path: Path, stage_x: float, stage_y: float):
        self.stage_x = stage_x
        self.stage_y = stage_y
        self.rows = {}
        self._load_csv(csv_path)

    def _load_csv(self, csv_path: Path):
        """Load coordinates from CSV file."""
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                section = row.get("SECTION", "").strip()
                row_num = row.get("ROW", "").strip()

                if not section or not row_num:
                    continue

                # Handle row numbers (some might be "GA" instead of numbers)
                try:
                    row_int = int(row_num)
                except ValueError:
                    row_int = row_num  # Keep as string for GA, etc.

                # Parse X coordinate (handle comma formatting)
                x_str = row.get("X", "0").replace(",", "")
                try:
                    x = float(x_str)
                except ValueError:
                    continue

                # Parse Y coordinate
                y_str = row.get("Y", "0").replace(",", "")
                try:
                    y = float(y_str)
                except ValueError:
                    continue

                key = (section, row_int)
                self.rows[key] = {"x": x, "y": y}

    def get_row_position(self, section: str, row: int) -> Optional[dict]:
        """Get the X, Y coordinates for a specific row."""
        return self.rows.get((section, row))

    def calculate_angle(self, x: float, y: float) -> float:
        """
        Calculate viewing angle from center (in degrees).
        Negative = left of center, Positive = right of center.

        This is based on the seat's X position relative to the stage center.
        """
        # Calculate horizontal offset from stage center
        dx = self.stage_x - x

        # Normalize to approximate angle (-45 to +45 degrees)
        # The exact scaling depends on venue geometry
        # For Red Rocks, X ranges from ~544 (back) to ~1851 (front)
        # Stage X is around 1850

        # Calculate as percentage of max offset, then scale to degrees
        max_offset = 600  # Approximate max horizontal spread
        angle = (dx / max_offset) * 45

        # Clamp to reasonable range
        return max(-45, min(45, angle))

    def get_distance_type(self, row: int, min_row: int = 1, max_row: int = 70) -> str:
        """Categorize row into front/middle/back."""
        total_rows = max_row - min_row
        position = (row - min_row) / total_rows

        if position < 0.3:
            return "front"
        elif position < 0.65:
            return "middle"
        else:
            return "back"

    def get_angle_type(self, angle: float) -> str:
        """Categorize angle into left/center/right."""
        if angle < -15:
            return "left"
        elif angle > 15:
            return "right"
        else:
            return "center"


def get_seat_position(
    csv_path: Path,
    stage_x: float,
    stage_y: float,
    section: str,
    row: int,
    row_range: Optional[dict] = None
) -> Optional[SeatPosition]:
    """
    Get complete position info for a seat.

    Args:
        csv_path: Path to coordinates CSV
        stage_x: X coordinate of stage center
        stage_y: Y coordinate of stage center
        section: Section name (e.g., "RESERVED")
        row: Row number
        row_range: Optional dict with min/max row numbers

    Returns:
        SeatPosition object or None if row not found
    """
    coords = CoordinateSystem(csv_path, stage_x, stage_y)
    pos = coords.get_row_position(section, row)

    if pos is None:
        return None

    angle = coords.calculate_angle(pos["x"], pos["y"])

    min_row = row_range.get("min", 1) if row_range else 1
    max_row = row_range.get("max", 70) if row_range else 70

    distance_type = coords.get_distance_type(row, min_row, max_row)
    angle_type = coords.get_angle_type(angle)

    return SeatPosition(
        section=section,
        row=row,
        x=pos["x"],
        y=pos["y"],
        angle=angle,
        distance_type=distance_type,
        angle_type=angle_type
    )


def list_available_rows(csv_path: Path, section: str = "RESERVED") -> list:
    """List all available row numbers for a section."""
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("SECTION", "").strip() == section:
                try:
                    row_num = int(row.get("ROW", "").strip())
                    rows.append(row_num)
                except ValueError:
                    pass
    return sorted(rows)
