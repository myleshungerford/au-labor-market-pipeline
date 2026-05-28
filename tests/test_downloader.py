import pytest
from src.acquire import downloader


def test_cache_hit_returns_without_network(tmp_path):
    dest = tmp_path / "already.txt"
    dest.write_text("cached")
    # No network needed; existing file is returned as-is.
    result = downloader.download("http://example.invalid/x", dest)
    assert result == dest
    assert dest.read_text() == "cached"


def test_missing_file_raises_when_download_fails(tmp_path, monkeypatch):
    dest = tmp_path / "missing.bin"

    class FakeResp:
        status_code = 404

        def raise_for_status(self):
            raise downloader.requests.HTTPError("404")

    monkeypatch.setattr(downloader.requests, "get", lambda *a, **k: FakeResp())
    with pytest.raises(downloader.requests.HTTPError):
        downloader.download("http://example.invalid/missing", dest, retries=1)
    assert not dest.exists()  # never leave a partial file
