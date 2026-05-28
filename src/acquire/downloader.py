import logging
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src import config

log = logging.getLogger(__name__)


def download(
    url: str,
    dest,
    *,
    headers: dict | None = None,
    force: bool = False,
    retries: int = 4,
) -> Path:
    """Download url to dest with caching and retries. Fails loud on non-2xx."""
    dest = Path(dest)
    if dest.exists() and not force:
        log.info("cache hit: %s", dest.name)
        return dest

    hdrs = {"User-Agent": config.USER_AGENT}
    if headers:
        hdrs.update(headers)

    @retry(
        stop=stop_after_attempt(retries),
        wait=wait_exponential(multiplier=1, max=30),
        reraise=True,
    )
    def _fetch() -> bytes:
        log.info("downloading %s", url)
        resp = requests.get(url, headers=hdrs, timeout=120)
        resp.raise_for_status()
        return resp.content

    content = _fetch()
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(content)
    tmp.replace(dest)  # atomic; no partial file on failure
    log.info("saved %s (%d bytes)", dest.name, len(content))
    return dest
