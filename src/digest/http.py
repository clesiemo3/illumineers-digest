import time

import httpx

USER_AGENT = "illumineers-digest/0.1 (personal weekly Lorcana newsletter)"

_last_request: dict[str, float] = {}


def client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"},
        follow_redirects=True,
        timeout=30,
    )


def get(c: httpx.Client, url: str, *, delay: float = 2.0, **kwargs) -> httpx.Response:
    """GET with a per-host delay so we never hammer anyone's site."""
    host = httpx.URL(url).host
    wait = _last_request.get(host, 0) + delay - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    resp = c.get(url, **kwargs)
    _last_request[host] = time.monotonic()
    resp.raise_for_status()
    return resp
