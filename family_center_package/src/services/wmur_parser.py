import re


class NewsInfo:
    def __init__(self, headline: str, summary: str = "", category: str = ""):
        self.headline = headline
        self.summary = summary
        self.category = category

    def to_dict(self) -> dict:
        return {
            "headline": self.headline,
            "summary": self.summary,
            "category": self.category,
        }


class WMURParser:
    def __init__(self) -> None:
        # More flexible pattern for news headlines
        self.headline_pattern = re.compile(
            r"([A-Za-z0-9'\-:.,() ]{10,})", re.IGNORECASE
        )
        # Pattern for breaking news indicators
        self.breaking_pattern = re.compile(
            r"(breaking|urgent|alert|update)", re.IGNORECASE
        )
        # Pattern for news categories
        self.category_pattern = re.compile(
            r"(weather|politics|sports|crime|business|health|education)", re.IGNORECASE
        )

    def parse_content(self, text: str) -> dict[str, list[NewsInfo]]:
        """Parse WMUR news content to extract headlines."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        news_items = []
        seen_headlines = set()  # To avoid duplicates

        for line in lines:
            # Skip very short lines or navigation elements
            if len(line) < 10 or any(
                x in line.lower()
                for x in [
                    "menu",
                    "search",
                    "login",
                    "sign up",
                    "subscribe",
                    "advertisement",
                    "share",
                    "comment",
                    "facebook",
                    "twitter",
                    "instagram",
                    "copy link",
                    "close",
                    "body of missing",
                    "fish and game says",
                    "wmur",
                    "consumer reports",
                    "by",
                    "and",
                    "min",
                    "hours ago",
                    "days ago",
                ]
            ):
                continue

            # Look for potential headlines (longer text that looks like news)
            potential_headlines = self._extract_potential_headlines(line)

            for headline in potential_headlines:
                # Clean up headline
                headline = self._clean_headline(headline)

                # Skip if too short, too long, or already seen
                if (
                    len(headline) < 15
                    or len(headline) > 200
                    or headline.lower() in seen_headlines
                ):
                    continue

                # Skip if contains unwanted words
                if any(
                    x in headline.lower()
                    for x in [
                        "click",
                        "read more",
                        "full story",
                        "video",
                        "photos",
                        "gallery",
                        "share",
                        "comment",
                        "facebook",
                        "twitter",
                        "instagram",
                        "copy link",
                        "close",
                        "advertisement",
                        "menu",
                        "search",
                        "login",
                        "sign up",
                        "subscribe",
                    ]
                ):
                    continue

                # Determine category
                category = self._determine_category(headline)

                # Create news info
                news_item = NewsInfo(headline=headline, summary="", category=category)
                news_items.append(news_item)
                seen_headlines.add(headline.lower())

        return {"news": news_items}

    def _extract_potential_headlines(self, line: str) -> list[str]:
        """Extract potential headlines from a line of text."""
        headlines = []

        # Split by common delimiters and look for substantial text
        parts = re.split(r"[|•\n\t]+", line)

        for part in parts:
            part = part.strip()
            if len(part) >= 15 and len(part) <= 200:
                # Check if it looks like a headline (starts with capital letter, has proper spacing)
                if (
                    part[0].isupper()
                    and " " in part
                    and not part.startswith("By ")
                    and not part.startswith("WMUR")
                    and not part.startswith("Share")
                    and not part.startswith("Copy")
                ):
                    headlines.append(part)

        return headlines

    def _clean_headline(self, headline: str) -> str:
        """Clean and format a headline."""
        # Remove extra whitespace and normalize
        headline = re.sub(r"\s+", " ", headline.strip())

        # Remove common prefixes/suffixes
        headline = re.sub(
            r"^(By\s+|WMUR\s+|Share\s+|Copy\s+)", "", headline, flags=re.IGNORECASE
        )
        headline = re.sub(
            r"(\s+WMUR\s*|\s+Share\s*|\s+Copy\s*)$", "", headline, flags=re.IGNORECASE
        )

        # Ensure proper capitalization
        headline = headline.title()

        return headline

    def _determine_category(self, text: str) -> str:
        """Determine the category of a news item based on content."""
        text_lower = text.lower()

        if any(
            word in text_lower
            for word in ["weather", "forecast", "storm", "rain", "snow", "temperature"]
        ):
            return "Weather"
        elif any(
            word in text_lower
            for word in [
                "politics",
                "election",
                "vote",
                "government",
                "congress",
                "senate",
            ]
        ):
            return "Politics"
        elif any(
            word in text_lower
            for word in ["sports", "game", "team", "player", "athlete"]
        ):
            return "Sports"
        elif any(
            word in text_lower
            for word in [
                "crime",
                "police",
                "arrest",
                "investigation",
                "missing",
                "found",
            ]
        ):
            return "Crime"
        elif any(
            word in text_lower
            for word in [
                "business",
                "economy",
                "market",
                "company",
                "tuition",
                "college",
            ]
        ):
            return "Business"
        elif any(
            word in text_lower
            for word in ["health", "medical", "hospital", "doctor", "covid"]
        ):
            return "Health"
        elif any(
            word in text_lower
            for word in ["education", "school", "student", "teacher", "academic"]
        ):
            return "Education"
        else:
            return "General"

    def create_formatted_content(self, parsed_data: dict[str, list[NewsInfo]]) -> dict:
        """Create formatted content for slide generation."""
        content = {"source": "WMUR News", "type": "news_headlines", "content": []}

        content_list = content["content"]
        for news_item in parsed_data.get("news", []):
            if isinstance(content_list, list):
                content_list.append(
                    {
                        "title": news_item.headline,
                        "summary": news_item.summary,
                        "category": news_item.category,
                        "type": "news",
                    }
                )

        return content


def parse_wmur_content(text: str) -> dict:
    """Parse WMUR news content and return formatted data."""
    parser = WMURParser()
    parsed_data = parser.parse_content(text)
    return parser.create_formatted_content(parsed_data)
