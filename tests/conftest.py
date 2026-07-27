"""Keep the deterministic test suite independent of utility websites."""

import pytest

from scrapers.base import BaseScraper


@pytest.fixture(autouse=True)
def block_unmocked_network(monkeypatch):
    """Tests that need source content explicitly mock these methods."""
    def blocked(*args, **kwargs):
        raise RuntimeError("live network disabled in deterministic tests")

    monkeypatch.setattr(BaseScraper, "fetch_page", blocked)
    monkeypatch.setattr(BaseScraper, "fetch_bytes", blocked)
