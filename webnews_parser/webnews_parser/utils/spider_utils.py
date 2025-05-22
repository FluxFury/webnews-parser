from html import unescape
import re
from unicodedata import normalize

from scrapy.http import Response


def css_mutator(selector: str, response: Response) -> str:
    """
    Safely extract data using CSS selector.

    Args:
        selector (str): CSS selector string.
        response (Response): Response object to extract from.

    Returns:
        str: Extracted value or empty string if not found.
    """
    placeholder = response.css(selector).get()
    return placeholder or ""


def xpath_mutator(selector: str, response: Response) -> str:
    """
    Safely extract data using XPath selector.

    Args:
        selector (str): XPath selector string.
        response (Response): Response object to extract from.

    Returns:
        str: Extracted value or empty string if not found.
    """
    placeholder = response.xpath(selector).get()
    return placeholder or ""


def xpath_mutator_all(selector: str, response: Response) -> list[str]:
    """
    Safely extract all data using XPath selector.

    Args:
        selector (str): XPath selector string.
        response (Response): Response object to extract from.

    Returns:
        list[str]: List of extracted values or empty list if not found.
    """
    placeholder = response.xpath(selector).getall()
    return placeholder or []


def clean_text(text: str | None) -> str:
    """
    Clean and format text content.

    Args:
        text (str | None): The text to clean.

    Returns:
        str: The cleaned text string.
    """
    if not text:
        return ""

    cleaned = (
        unescape(text)
        .replace("\u2060", "")
        .replace("\\\\", "")
        .replace("\\", "")
        .replace("]", "")
        .replace("[", "")
        .replace("\\\\u2019", "'")
        .strip()
    )
    return normalize("NFKD", cleaned)


def extract_teams(url):
    pattern = r"/([^/-]+(?:-[^/-]+)*)-vs-([^/-]+(?:-[^/-]+)*)-\d+$"
    match = re.search(pattern, url)
    if match:
        team1 = match.group(1)
        team2 = match.group(2)
        return team1, team2
    else:
        return None, None
