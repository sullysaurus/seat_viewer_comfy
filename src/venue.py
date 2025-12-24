"""
Venue configuration loader.
Loads venue YAML configs and provides access to venue data.
"""

import yaml
from pathlib import Path
from typing import Optional


class VenueConfig:
    """Represents a venue's configuration."""

    def __init__(self, config_path: Path):
        with open(config_path) as f:
            self._config = yaml.safe_load(f)

        self.id = self._config["venue"]["id"]
        self.name = self._config["venue"]["name"]
        self.venue_type = self._config["venue"]["type"]

    @property
    def csv_path(self) -> str:
        return self._config["coordinates"]["csv_path"]

    @property
    def stage_position(self) -> dict:
        return self._config["coordinates"]["stage_position"]

    @property
    def row_range(self) -> dict:
        return self._config["coordinates"]["row_range"]

    @property
    def reference_images(self) -> list:
        return self._config["reference_images"]

    @property
    def prompts(self) -> dict:
        return self._config["prompts"]

    @property
    def output_config(self) -> dict:
        return self._config["output"]

    def get_prompt_elements(self) -> list:
        """Get the list of venue-specific prompt elements."""
        return self.prompts.get("elements", [])

    def get_negative_prompt(self) -> str:
        """Get the negative prompt for this venue."""
        return self.prompts.get("negative", "")

    def get_distance_description(self, distance_type: str) -> str:
        """Get description for front/middle/back distance."""
        return self.prompts.get("distance_descriptions", {}).get(distance_type, "")

    def get_angle_description(self, angle_type: str) -> str:
        """Get description for left/center/right angle."""
        return self.prompts.get("angle_descriptions", {}).get(angle_type, "")


def load_venue(venue_id: str, config_dir: Optional[Path] = None) -> VenueConfig:
    """
    Load a venue configuration by ID.

    Args:
        venue_id: The venue identifier (e.g., "red_rocks")
        config_dir: Optional path to config directory. Defaults to project config/venues/

    Returns:
        VenueConfig object
    """
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config" / "venues"

    config_path = config_dir / f"{venue_id}.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Venue config not found: {config_path}")

    return VenueConfig(config_path)


def list_venues(config_dir: Optional[Path] = None) -> list:
    """List all available venue IDs."""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config" / "venues"

    return [p.stem for p in config_dir.glob("*.yaml")]
