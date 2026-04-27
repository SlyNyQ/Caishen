from __future__ import annotations
import time
import random
import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TabularAutofillBot/0.1; +local-dev)"
}

def fetch_html(url: str, timeout_s: int = 20) -> str:
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout_s)
    r.raise_for_status()
    return r.text

def html_to_text(html: str, max_chars: int = 60_000) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove obvious noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n")
    # Clean excessive blank lines
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    cleaned = "\n".join(lines)

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n[TRUNCATED]"
    return cleaned

def polite_delay(min_s=0.4, max_s=1.2):
    time.sleep(random.uniform(min_s, max_s))