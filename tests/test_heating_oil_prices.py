"""Heating-oil price refresh for the spark gap (scripts/fetch_heating_oil.py; owner decisions 149-152, 2026-11-26).

Offline: a saved answer of Statistics Canada's Web Data Service for the six city series (two months, retrieved
2026-11-26, tests/fixtures/statcan_heating_oil_wds.json); the network is replaced by a stand-in.
"""
import copy
import json
from pathlib import Path

import pytest

from scripts import fetch_heating_oil as oil

ANSWER = json.loads((Path(__file__).resolve().parent / "fixtures" / "statcan_heating_oil_wds.json")
                    .read_text(encoding="utf-8"))


class Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise oil.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.body


def post(answer=ANSWER):
    calls = []

    def fake(url, json=None, headers=None, timeout=None):
        calls.append(json)
        return Response(copy.deepcopy(answer))
    fake.calls = calls
    return fake


def test_parse_reads_every_city_and_never_stores_unavailable_values():
    months = oil.parse(ANSWER)
    assert set(months) == set(oil.SERIES)
    assert months["NS"]["2026-10"]["value"] == 248.1 and months["NB"]["2026-10"]["value"] == 268.7
    changed = copy.deepcopy(ANSWER)
    point = changed[0]["object"]["vectorDataPoint"][-1]
    point.update(statusCode=1, value=None)
    region = next(r for r, (vector, _) in oil.SERIES.items() if vector == changed[0]["object"]["vectorId"])
    assert oil.parse(changed)[region][point["refPer"][:7]] == {"value": None, "status": "..", "symbol": None,
                                                              "release_time": point["releaseTime"]}
    wrong = copy.deepcopy(ANSWER)
    wrong[0]["object"]["productId"] = 18100004
    with pytest.raises(ValueError, match="unexpected series"):
        oil.parse(wrong)


def test_refresh_adds_months_keeps_history_and_stops_on_revisions(tmp_path):
    path = tmp_path / "heating_oil_prices.json"
    assert len(oil.refresh(path, dry_run=True, post=post())) == 12 and not path.exists()
    first = post()
    assert len(oil.refresh(path, dry_run=False, post=first)) == 12
    assert first.calls[0][0]["latestN"] == oil.FIRST_MONTHS
    saved = path.read_text(encoding="utf-8")
    again = post()
    assert oil.refresh(path, dry_run=False, post=again) == [] and path.read_text(encoding="utf-8") == saved
    assert again.calls[0][0]["latestN"] == oil.UPDATE_MONTHS
    revised = copy.deepcopy(ANSWER)
    revised[0]["object"]["vectorDataPoint"][-1]["value"] += 1.0
    with pytest.raises(oil.RevisionError, match="review"):
        oil.refresh(path, dry_run=False, post=post(revised))
    assert path.read_text(encoding="utf-8") == saved
    document = json.loads(saved)
    assert document["kind"] == "heating_oil_prices" and document["series"]["NS"]["months"]["2026-10"]["value"] == 248.1


def test_failed_download_keeps_the_last_file(tmp_path, monkeypatch, capsys):
    path = tmp_path / "heating_oil_prices.json"
    path.write_text(json.dumps(oil.empty_document()) + "\n", encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    def down(*args, **kwargs):
        return Response({"message": "Too Many Requests"}, status=430)
    monkeypatch.setattr(oil.requests, "post", down)
    monkeypatch.setattr(oil.time, "sleep", lambda seconds: None)
    assert oil.main(["--output", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == before and "left unchanged" in capsys.readouterr().err
