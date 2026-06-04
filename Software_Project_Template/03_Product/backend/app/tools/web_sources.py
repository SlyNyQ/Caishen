from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import socket
from typing import Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests


class UnsafeSourceUrl(ValueError):
    pass


def _resolve_addresses(hostname: str) -> list[str]:
    return list(
        dict.fromkeys(
            result[4][0]
            for result in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        )
    )


def validate_public_url(
    url: str,
    *,
    resolver: Callable[[str], list[str]] = _resolve_addresses,
) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeSourceUrl("Only public HTTP and HTTPS source URLs are supported.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeSourceUrl("The source URL must contain a public hostname without credentials.")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".local"):
        raise UnsafeSourceUrl("Local and private-network source URLs are blocked.")
    try:
        addresses = resolver(hostname)
    except OSError as exc:
        raise UnsafeSourceUrl(f"The source hostname could not be resolved: {hostname}.") from exc
    if not addresses:
        raise UnsafeSourceUrl(f"The source hostname could not be resolved: {hostname}.")
    for raw_address in addresses:
        address = ipaddress.ip_address(raw_address)
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise UnsafeSourceUrl("Local and private-network source URLs are blocked.")
    return parsed.geturl()


@dataclass(slots=True)
class PublicSourceFetcher:
    timeout_seconds: int = 20
    max_bytes: int = 1_000_000
    max_redirects: int = 3

    def fetch(self, url: str) -> dict[str, str]:
        current_url = validate_public_url(url)
        response = None
        for _ in range(self.max_redirects + 1):
            response = requests.get(
                current_url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "CaishenResearch/1.0"},
                allow_redirects=False,
                stream=True,
            )
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise RuntimeError("The source returned an empty redirect.")
                current_url = validate_public_url(urljoin(current_url, location))
                continue
            break
        if response is None or response.is_redirect:
            raise RuntimeError("The source exceeded the redirect limit.")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if not any(kind in content_type for kind in ("text/html", "text/plain", "application/xhtml+xml")):
            raise RuntimeError(f"Unsupported source content type: {content_type or 'unknown'}.")

        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=32_768):
            total += len(chunk)
            if total > self.max_bytes:
                raise RuntimeError("The source exceeded the configured size limit.")
            chunks.append(chunk)
        html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "form", "nav", "footer"]):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else current_url
        text = " ".join(soup.get_text(" ", strip=True).split())
        return {
            "url": current_url,
            "title": title[:180],
            "summary": text[:1200] or "No readable source text was found.",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status": "available",
        }


def unavailable_source(url: str, detail: str) -> dict[str, str]:
    return {
        "url": url,
        "title": url,
        "summary": detail,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status": "unavailable",
    }
