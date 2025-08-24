import re


class MovieInfo:
    def __init__(self, title: str, section: str):
        self.title = title
        self.section = section

    def to_dict(self) -> dict[str, str]:
        return {"title": self.title, "section": self.section}


class RedRiverParser:
    def __init__(self) -> None:
        # HTML selectors for movie titles based on analysis
        self.movie_title_selectors = [
            ".podsfilmtitle",  # Primary selector based on HTML analysis
            "[class*='title']",
            "[class*='movie']",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",  # Fallback to headings
        ]

        # Pattern for duration/rating info
        self.duration_pattern = re.compile(r"\(\d+ min.*?\) ?\d{4}", re.IGNORECASE)

        # Pattern for events like "Creative Guts Short Film Festival 2025"
        self.event_pattern = re.compile(
            r"([A-Za-z0-9'\-: ]+Film Festival) ?\d{4,}", re.IGNORECASE
        )

    def parse_content(self, text: str) -> dict[str, list[MovieInfo]]:
        """Parse content using improved text analysis."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sections = self._find_sections(lines)
        results: dict[str, list[MovieInfo]] = {"now_playing": [], "coming_up": []}

        for section_name, section_text in sections.items():
            movies = self._parse_section_improved(section_text, section_name)
            if section_name == "now_playing":
                results["now_playing"] = movies
            elif section_name == "coming_up":
                results["coming_up"] = movies

        return results

    def _find_sections(self, lines: list[str]) -> dict[str, str]:
        """Find Now Playing and Coming Up sections in the text."""
        sections = {"now_playing": "", "coming_up": ""}
        current_section = None
        current_text: list[str] = []

        for line in lines:
            if re.search(r"^Now Playing:", line, re.IGNORECASE):
                if current_section and current_text:
                    sections[current_section] = " ".join(current_text)
                current_section = "now_playing"
                current_text = []
                continue
            elif re.search(r"^Coming Up:", line, re.IGNORECASE):
                if current_section and current_text:
                    sections[current_section] = " ".join(current_text)
                current_section = "coming_up"
                current_text = []
                continue
            if current_section:
                current_text.append(line)

        if current_section and current_text:
            sections[current_section] = " ".join(current_text)

        return sections

    def _parse_section_improved(self, text: str, section_name: str) -> list[MovieInfo]:
        """Improved parsing that looks for movie titles more intelligently."""
        movies = []
        found_titles = set()

        # Split text into lines and analyze each line
        lines = text.split("\n")

        for _i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 3:
                continue

            # Skip lines that are clearly not movie titles
            if any(
                x in line.lower()
                for x in [
                    "screen",
                    "see all showtimes",
                    "pm",
                    "am",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                    "monday",
                    "tuesday",
                    "min",
                    "pg-",
                    "2025",
                    "now playing",
                    "coming up",
                    "thursday,",
                    "friday,",
                    "saturday,",
                    "sunday,",
                ]
            ):
                continue

            # Skip lines that start or end with parentheses (duration/rating info)
            if line.startswith("(") or line.endswith(")"):
                continue

            # Skip lines that are too short or too long for movie titles
            if len(line) < 3 or len(line) > 100:
                continue

            # Skip lines that are just dates
            if re.match(r"^[A-Za-z]+,?\s+[A-Za-z]+\s+\d{1,2}$", line):
                continue

            # Clean up the title
            title = line.strip(" -:.").title()

            # Additional validation: check if this looks like a movie title
            if (
                title
                and title.lower() not in found_titles
                and not any(
                    x in title.lower()
                    for x in ["click", "read more", "full story", "video", "photos"]
                )
                and
                # Movie titles should have proper words, not just numbers or single letters
                len(title.split()) >= 1
                and
                # Check if it's not just a date or time
                not re.match(r"^\d{1,2}:\d{2}", title)
                and not re.match(r"^\d{1,2}/\d{1,2}", title)
            ):
                movies.append(
                    MovieInfo(
                        title=title, section=section_name.replace("_", " ").title()
                    )
                )
                found_titles.add(title.lower())

        # For events (e.g. "Creative Guts Short Film Festival 2025")
        for match in self.event_pattern.finditer(text):
            raw_title = match.group(1).strip()
            title = raw_title.strip(" -:.").title()
            # Clean up any remaining showtime fragments
            if "screen" in title.lower() or "pm" in title.lower():
                # Remove everything after "Screen" or time indicators
                title = re.sub(r"\s+Screen.*$", "", title, flags=re.IGNORECASE)
                title = re.sub(
                    r"\s+\d{1,2}:\d{2}\s+[AP]M.*$", "", title, flags=re.IGNORECASE
                )
                title = title.strip(" -:.")
            if title and title.lower() not in found_titles:
                movies.append(
                    MovieInfo(
                        title=title, section=section_name.replace("_", " ").title()
                    )
                )
                found_titles.add(title.lower())

        return movies

    def create_formatted_content(
        self, parsed_data: dict[str, list[MovieInfo]]
    ) -> dict[str, str | list[dict[str, str]]]:
        """Create formatted content for slide generation."""
        content: dict[str, str | list[dict[str, str]]] = {
            "source": "Red River Theater",
            "type": "theater_movies",
            "content": [],
        }

        content_list = content["content"]
        if isinstance(content_list, list):
            for movie in parsed_data.get("now_playing", []):
                content_list.append(
                    {"title": movie.title, "section": "Now Playing", "type": "movie"}
                )

            for movie in parsed_data.get("coming_up", []):
                content_list.append(
                    {"title": movie.title, "section": "Coming Up", "type": "movie"}
                )

        return content


def parse_red_river_content(text: str) -> dict[str, str | list[dict[str, str]]]:
    """Parse Red River Theater content and return formatted data."""
    parser = RedRiverParser()
    parsed_data = parser.parse_content(text)
    return parser.create_formatted_content(parsed_data)
