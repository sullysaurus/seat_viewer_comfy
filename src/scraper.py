"""
Scraper for A View From My Seat website.
Fetches venue sections and seat view photos.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional, List, Tuple
from urllib.parse import quote_plus


@dataclass
class SeatPhoto:
    """Represents a photo from a specific seat."""
    image_url: str
    section: str
    row: Optional[str]
    seat: Optional[str]
    event: Optional[str]
    venue: str
    photo_page_url: str


@dataclass
class Section:
    """Represents a venue section."""
    name: str
    photo_count: int
    url: str


class AVFMSScraper:
    """Scraper for aviewfrommyseat.com"""

    BASE_URL = "https://aviewfrommyseat.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, delay: float = 1.0):
        """
        Initialize scraper with rate limiting.

        Args:
            delay: Seconds to wait between requests (be respectful)
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _get(self, url: str) -> Optional[BeautifulSoup]:
        """Make a GET request and return parsed HTML."""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as e:
            print(f"Request failed for {url}: {e}")
            return None

    def search_venues(self, query: str) -> List[dict]:
        """
        Search for venues by name.

        Args:
            query: Search term (e.g., "Lenovo Center")

        Returns:
            List of venue dicts with name and url
        """
        search_url = f"{self.BASE_URL}/search.php?q={quote_plus(query)}"
        soup = self._get(search_url)

        if not soup:
            return []

        venues = []
        # Look for venue links in search results
        venue_links = soup.select("a[href*='/venue/']")

        seen = set()
        for link in venue_links:
            href = link.get("href", "")
            name = link.get_text(strip=True)

            # Skip if already seen or empty
            if not name or href in seen:
                continue

            # Make sure it's a venue page, not a photo page
            if "/venue/" in href and "/section" not in href.lower():
                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                venues.append({"name": name, "url": full_url})
                seen.add(href)

        return venues

    def get_venue_sections(self, venue_url: str) -> List[Section]:
        """
        Get all sections for a venue.

        Args:
            venue_url: URL to venue page (e.g., https://aviewfrommyseat.com/venue/Lenovo+Center/)

        Returns:
            List of Section objects
        """
        # Ensure we're hitting the sections page
        if not venue_url.endswith("/"):
            venue_url += "/"
        sections_url = venue_url.rstrip("/") + "/sections/"

        soup = self._get(sections_url)
        if not soup:
            return []

        sections = []

        # Find section containers - they have class 'section_contained_in' with section_name attribute
        section_containers = soup.select(".section_contained_in[section_name]")

        for container in section_containers:
            section_name = container.get("section_name", "")
            if not section_name:
                continue

            # Find the link inside
            link = container.select_one("a[href*='/venue/']")
            if not link:
                continue

            href = link.get("href", "")

            # Extract photo count from text like "(34)"
            container_text = container.get_text()
            photo_match = re.search(r'\((\d+)\)', container_text)
            photo_count = int(photo_match.group(1)) if photo_match else 0

            # Skip sections with no photos
            if photo_count == 0:
                continue

            full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            sections.append(Section(
                name=section_name,
                photo_count=photo_count,
                url=full_url
            ))

        # Sort by section name (try numeric sort if possible)
        def sort_key(s):
            # Try to extract number from section name for numeric sorting
            match = re.search(r'(\d+)', s.name)
            if match:
                return (0, int(match.group(1)), s.name)
            return (1, 0, s.name)

        sections.sort(key=sort_key)

        return sections

    def get_section_photos(self, section_url: str, venue_name: str = "", max_photos: int = 20) -> List[SeatPhoto]:
        """
        Get photos from a specific section.

        Args:
            section_url: URL to section page
            venue_name: Name of venue for metadata
            max_photos: Maximum number of photos to fetch

        Returns:
            List of SeatPhoto objects
        """
        soup = self._get(section_url)
        if not soup:
            return []

        photos = []

        # Find photo thumbnails/links
        photo_links = soup.select("a[href*='/photo/']")

        for link in photo_links[:max_photos]:
            href = link.get("href", "")
            if not href:
                continue

            photo_page_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            # Try to get the image directly from thumbnail
            img = link.select_one("img")
            if img:
                img_src = img.get("src", "")
                if img_src:
                    # Convert thumbnail to full image URL if needed
                    if "thumb" in img_src.lower():
                        img_src = img_src.replace("_thumb", "").replace("_small", "")

                    if not img_src.startswith("http"):
                        img_src = f"{self.BASE_URL}{img_src}"

                    # Parse section/row/seat from URL
                    section, row, seat = self._parse_seat_info(photo_page_url)

                    photos.append(SeatPhoto(
                        image_url=img_src,
                        section=section,
                        row=row,
                        seat=seat,
                        event=None,
                        venue=venue_name,
                        photo_page_url=photo_page_url
                    ))

        return photos

    def get_photo_details(self, photo_url: str) -> Optional[SeatPhoto]:
        """
        Get full details for a specific photo page.

        Args:
            photo_url: URL to individual photo page

        Returns:
            SeatPhoto with full details, or None
        """
        soup = self._get(photo_url)
        if not soup:
            return None

        # Find the main image
        main_img = soup.select_one("img.photo, img[src*='/photos/']")
        if not main_img:
            # Try other selectors
            main_img = soup.select_one(".photo-container img, #photo img")

        if not main_img:
            return None

        img_src = main_img.get("src", "")
        if not img_src.startswith("http"):
            img_src = f"{self.BASE_URL}{img_src}"

        # Parse info from URL and page
        section, row, seat = self._parse_seat_info(photo_url)

        # Try to get event name from page
        event = None
        event_elem = soup.select_one(".event-name, .tour-name, h2")
        if event_elem:
            event = event_elem.get_text(strip=True)

        # Get venue name
        venue = ""
        venue_elem = soup.select_one("a[href*='/venue/']")
        if venue_elem:
            venue = venue_elem.get_text(strip=True)

        return SeatPhoto(
            image_url=img_src,
            section=section,
            row=row,
            seat=seat,
            event=event,
            venue=venue,
            photo_page_url=photo_url
        )

    def _parse_seat_info(self, url: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Parse section, row, seat from a photo URL."""
        section = ""
        row = None
        seat = None

        # Pattern: /section-XXX/row-YYY/seat-ZZZ/
        section_match = re.search(r'section[/-]([^/]+)', url, re.IGNORECASE)
        row_match = re.search(r'row[/-]([^/]+)', url, re.IGNORECASE)
        seat_match = re.search(r'seat[/-]([^/]+)', url, re.IGNORECASE)

        if section_match:
            section = section_match.group(1).replace("-", " ").replace("+", " ")
        if row_match:
            row = row_match.group(1).replace("-", " ").replace("+", " ")
        if seat_match:
            seat = seat_match.group(1).replace("-", " ").replace("+", " ")

        return section, row, seat

    def download_image(self, image_url: str, save_path: str) -> bool:
        """
        Download an image to local file.

        Args:
            image_url: URL of image to download
            save_path: Local path to save image

        Returns:
            True if successful, False otherwise
        """
        try:
            time.sleep(self.delay)
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

            return True
        except Exception as e:
            print(f"Failed to download {image_url}: {e}")
            return False
