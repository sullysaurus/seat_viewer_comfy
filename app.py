"""
Streamlit app for fetching seat view photos from A View From My Seat.
Use these as reference images for FLUX.2 image generation.

Deployable to Streamlit Cloud.
"""

import io
import zipfile
from datetime import datetime
from typing import List, Tuple, Optional

import requests
import streamlit as st

from src.scraper import AVFMSScraper, SeatPhoto


@st.cache_resource
def get_scraper():
    """Get cached scraper instance."""
    return AVFMSScraper(delay=0.5)


def fetch_image_bytes(url: str, scraper: AVFMSScraper) -> Optional[bytes]:
    """Download image and return as bytes."""
    try:
        response = scraper.session.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Failed to download image: {e}")
        return None


def create_zip_of_photos(photos: List[Tuple[str, bytes]]) -> bytes:
    """Create a zip file containing all photos."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, image_bytes in photos:
            zf.writestr(filename, image_bytes)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def main():
    st.set_page_config(
        page_title="View From My Seat - Reference Images",
        page_icon="🎫",
        layout="wide"
    )

    st.title("🎫 Seat View Reference Images")
    st.markdown(
        "Fetch photos from [A View From My Seat](https://aviewfrommyseat.com) "
        "to use as reference images for AI image generation."
    )

    scraper = get_scraper()

    # Initialize session state
    if "venues" not in st.session_state:
        st.session_state.venues = []
    if "sections" not in st.session_state:
        st.session_state.sections = []
    if "photos" not in st.session_state:
        st.session_state.photos = []
    if "current_venue" not in st.session_state:
        st.session_state.current_venue = None
    if "downloaded_images" not in st.session_state:
        st.session_state.downloaded_images = []

    # Sidebar for venue search
    with st.sidebar:
        st.header("🔍 Find Venue")

        venue_query = st.text_input(
            "Search venue",
            placeholder="e.g., Lenovo Center, Madison Square Garden",
            key="venue_search"
        )

        if st.button("Search", type="primary") and venue_query:
            with st.spinner("Searching venues..."):
                venues = scraper.search_venues(venue_query)
                st.session_state.venues = venues
                st.session_state.sections = []
                st.session_state.photos = []
                st.session_state.downloaded_images = []

        # Display venue results
        if st.session_state.venues:
            st.subheader("Select Venue")
            venue_names = [v["name"] for v in st.session_state.venues]

            selected_venue_name = st.selectbox(
                "Venue",
                options=venue_names,
                key="selected_venue"
            )

            if selected_venue_name:
                selected_venue = next(
                    (v for v in st.session_state.venues if v["name"] == selected_venue_name),
                    None
                )

                if selected_venue and st.button("Load Sections"):
                    with st.spinner("Loading sections..."):
                        sections = scraper.get_venue_sections(selected_venue["url"])
                        st.session_state.sections = sections
                        st.session_state.current_venue = selected_venue
                        st.session_state.photos = []
                        st.session_state.downloaded_images = []

        # Display section selector
        if st.session_state.sections:
            st.subheader("Select Section")

            # Filter to sections with photos
            sections_with_photos = [s for s in st.session_state.sections if s.photo_count > 0]

            if sections_with_photos:
                section_options = [f"{s.name} ({s.photo_count} photos)" for s in sections_with_photos]

                selected_section_str = st.selectbox(
                    "Section",
                    options=section_options,
                    key="selected_section"
                )

                if selected_section_str:
                    idx = section_options.index(selected_section_str)
                    selected_section = sections_with_photos[idx]

                    max_photos = st.slider("Max photos to fetch", 1, 20, 10)

                    if st.button("Fetch Photos"):
                        with st.spinner(f"Fetching photos from {selected_section.name}..."):
                            photos = scraper.get_section_photos(
                                selected_section.url,
                                venue_name=st.session_state.current_venue["name"],
                                max_photos=max_photos
                            )
                            st.session_state.photos = photos
                            st.session_state.downloaded_images = []
            else:
                st.info("No sections with photos found")

        st.divider()
        st.markdown("### How to use")
        st.markdown("""
        1. Search for a venue
        2. Select venue and load sections
        3. Pick a section and fetch photos
        4. Download photos for use as AI reference images
        """)

    # Main content area - display photos
    if st.session_state.photos:
        photos = st.session_state.photos
        venue_name = st.session_state.current_venue["name"] if st.session_state.current_venue else "venue"

        st.subheader(f"📸 {len(photos)} Photos Found")

        # Download all button at top
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📥 Prepare All for Download", type="primary"):
                with st.spinner("Downloading all images..."):
                    downloaded = []
                    progress = st.progress(0)

                    for idx, photo in enumerate(photos):
                        image_bytes = fetch_image_bytes(photo.image_url, scraper)
                        if image_bytes:
                            safe_venue = "".join(c if c.isalnum() else "_" for c in venue_name)
                            safe_section = "".join(c if c.isalnum() else "_" for c in photo.section)
                            filename = f"{safe_venue}_{safe_section}_{idx+1}.jpg"
                            downloaded.append((filename, image_bytes))
                        progress.progress((idx + 1) / len(photos))

                    st.session_state.downloaded_images = downloaded
                    st.success(f"Prepared {len(downloaded)} images!")

        # Show download button if images are ready
        if st.session_state.downloaded_images:
            zip_bytes = create_zip_of_photos(st.session_state.downloaded_images)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_venue = "".join(c if c.isalnum() else "_" for c in venue_name)

            with col2:
                st.download_button(
                    label=f"⬇️ Download All ({len(st.session_state.downloaded_images)} photos)",
                    data=zip_bytes,
                    file_name=f"{safe_venue}_reference_images_{timestamp}.zip",
                    mime="application/zip"
                )

        st.divider()

        # Display photos in grid
        cols = st.columns(3)

        for idx, photo in enumerate(photos):
            col = cols[idx % 3]

            with col:
                # Use use_column_width for compatibility with older Streamlit versions
                st.image(photo.image_url, use_column_width=True)

                # Photo info
                info_parts = [f"Section {photo.section}"]
                if photo.row:
                    info_parts.append(f"Row {photo.row}")
                if photo.seat:
                    info_parts.append(f"Seat {photo.seat}")

                st.caption(" | ".join(info_parts))

                # Individual download button
                if st.button(f"Download", key=f"dl_{idx}"):
                    image_bytes = fetch_image_bytes(photo.image_url, scraper)
                    if image_bytes:
                        safe_venue = "".join(c if c.isalnum() else "_" for c in venue_name)
                        safe_section = "".join(c if c.isalnum() else "_" for c in photo.section)
                        filename = f"{safe_venue}_{safe_section}_{idx+1}.jpg"

                        st.download_button(
                            label="⬇️ Save",
                            data=image_bytes,
                            file_name=filename,
                            mime="image/jpeg",
                            key=f"save_{idx}"
                        )

    else:
        # Empty state
        st.info("👈 Use the sidebar to search for a venue and select a section to fetch seat view photos.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            ### Quick Start

            1. **Search** for a venue (e.g., "Lenovo Center", "Red Rocks")
            2. **Select** the venue from results
            3. **Load sections** to see available seating areas
            4. **Choose a section** and fetch photos
            5. **Download** photos to use as reference images
            """)

        with col2:
            st.markdown("""
            ### Tips

            - Sections with more photos give you more perspective options
            - Lower sections (100s) = closer views
            - Upper sections (300s) = wider arena views
            - Use multiple photos from same section for consistency
            """)

        st.divider()
        st.markdown("""
        ### Popular Venues to Try
        - Madison Square Garden
        - Red Rocks Amphitheatre
        - Lenovo Center
        - TD Garden
        - Crypto.com Arena
        """)


if __name__ == "__main__":
    main()
