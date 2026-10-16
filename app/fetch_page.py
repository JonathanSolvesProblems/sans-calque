"""Fetch a public web page and return its text blocks, for "translate this page".

This runs on a shared server, so the URL is treated as hostile. Only http(s) on ports 80 and
443; every hostname is resolved first and refused if any address is private, loopback,
link-local or otherwise not a public unicast address; redirects are followed by hand, at most
three, each hop re-checked; the body is capped at 1 MB and must be HTML.
"""
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

MAX_BYTES = 1_000_000
UA = "sans-calque page fetch (translation demo; contact via github.com/JonathanSolvesProblems/sans-calque)"


class FetchError(ValueError):
    pass


def _check(url: str) -> str:
    u = urlsplit(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise FetchError("Only http and https page addresses are accepted.")
    if u.port not in (None, 80, 443):
        raise FetchError("Only the standard web ports are accepted.")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise FetchError("That address does not resolve.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise FetchError("That address points at a private network, so it was not fetched.")
    return url


def _peer_is_public(r: requests.Response) -> bool:
    """Check the address the socket actually connected to. The pre-check resolves the name
    once and the connection resolves it again, so a rebinding DNS answer could slip a private
    address in between; this closes that gap. If the peer cannot be read, refuse."""
    try:
        sock = r.raw._connection.sock
        return ipaddress.ip_address(sock.getpeername()[0]).is_global
    except Exception:
        return False


def _get(url: str) -> requests.Response:
    for _ in range(4):
        _check(url)
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15, stream=True, allow_redirects=False)
        if r.is_redirect or r.is_permanent_redirect:
            # nothing from a redirect is read except its Location, which goes through every
            # check again on the next hop; urllib3 has already released its socket anyway
            url = urljoin(url, r.headers.get("location", ""))
            r.close()
            continue
        if not _peer_is_public(r):  # this response's body will be read: verify where it came from
            r.close()
            raise FetchError("That address points at a private network, so it was not fetched.")
        return r
    raise FetchError("Too many redirects.")


def blocks_from_url(url: str) -> dict:
    r = _get(url.strip())
    if r.status_code != 200:
        raise FetchError(f"The page answered {r.status_code}.")
    if "html" not in r.headers.get("content-type", ""):
        raise FetchError("That address is not an HTML page.")
    body = b""
    for chunk in r.iter_content(65536):
        body += chunk
        if len(body) > MAX_BYTES:
            raise FetchError("That page is larger than 1 MB.")
    # bytes go to BeautifulSoup, which reads the page's own <meta charset>; a charset in the
    # header wins when the server sends one (requests' guess would re-read the consumed stream)
    declared = requests.utils.get_encoding_from_headers(r.headers)
    declared = None if declared == "ISO-8859-1" and "charset" not in r.headers.get("content-type", "").lower() else declared
    soup = BeautifulSoup(body, "lxml", from_encoding=declared)
    main = soup.find("main") or soup.body or soup
    for el in main.select("nav, header, footer, script, style, noscript, form"):
        el.decompose()
    out = []
    for el in main.find_all(["h1", "h2", "h3", "p", "li"]):
        if el.find(["p", "li"]):
            continue
        t = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        if len(t.split()) >= 4 and t not in out:
            out.append(t)
    title = soup.title.get_text(strip=True) if soup.title else url
    lang = ((soup.html.get("lang") if soup.html else "") or "").lower()
    en_twin = None
    for link in soup.find_all("link", attrs={"rel": "alternate", "hreflang": True}):
        if link["hreflang"].lower().startswith("en") and link.get("href"):
            en_twin = urljoin(r.url, link["href"])
            break
    return {"url": r.url, "title": title, "blocks": out, "lang": lang, "en_twin": en_twin}
