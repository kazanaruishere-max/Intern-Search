import csv
import json

from pkl_research.exporter import (
    companies_to_csv,
    companies_to_json,
    drafts_markdown,
    report_markdown,
)
from pkl_research.models import Company


def make_companies():
    return [
        Company(
            place_id="p1", name="PT A", category="Software house", rating=5.0,
            review_count=10, address="Jakarta Selatan", role_fit=["software"],
            maps_url="https://maps", distance_km=1.2,
        ),
        Company(
            place_id="p2", name="PT B", category="AI company", rating=4.6,
            review_count=20, address="Jakarta Pusat", role_fit=["ai"],
            maps_url="https://maps2", distance_km=5.0,
        ),
    ]


def test_csv_writes(tmp_path):
    path = tmp_path / "out.csv"
    companies_to_csv(make_companies(), path)
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["name"] == "PT A"
    assert rows[0]["role_fit"] == "software"
    assert rows[0]["rating"] == "5.0"


def test_json_writes(tmp_path):
    path = tmp_path / "out.json"
    companies_to_json(make_companies(), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["role_fit"] == ["software"]


def test_report_markdown(tmp_path):
    path = tmp_path / "report.md"
    report_markdown(make_companies(), path)
    text = path.read_text(encoding="utf-8")
    assert "## PT A" in text
    assert "5.0" in text
    assert "https://maps" in text


def test_drafts_markdown(tmp_path):
    path = tmp_path / "drafts.md"
    drafts = {"PT A": {"formal": "Halo PT A...", "casual": "Hai PT A..."}}
    drafts_markdown(drafts, path)
    text = path.read_text(encoding="utf-8")
    assert "## PT A" in text
    assert "### Varian: formal" in text
