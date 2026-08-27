from unittest.mock import patch

from pkl_research.scraper.vacancy_sources.ashby import AshbySource
from pkl_research.scraper.vacancy_sources.greenhouse import GreenhouseSource
from pkl_research.scraper.vacancy_sources.himalayas import HimalayasSource
from pkl_research.scraper.vacancy_sources.lever import LeverSource
from pkl_research.scraper.vacancy_sources.remoteok import RemoteokSource
from pkl_research.scraper.vacancy_sources.remotive import RemotiveSource
from pkl_research.scraper.vacancy_sources.wwr import WwrSource


@patch("pkl_research.scraper.vacancy_sources.remotive.fetch_json")
def test_remotive_parser(mock_fetch):
    mock_fetch.return_value = {
        "jobs": [
            {
                "id": 101,
                "title": "Software Engineer Intern",
                "company_name": "Acme Corp",
                "candidate_required_location": "Remote",
                "job_type": "internship",
                "salary": "$50k - $70k",
                "publication_date": "2026-08-10T12:00:00Z",
                "description": "Clean code developer",
                "tags": ["python", "django"],
                "url": "http://example.com/job1",
            }
        ]
    }
    src = RemotiveSource()
    res = src.fetch("software", limit=10)
    assert len(res) == 1
    v = res[0]
    assert v.source == "remotive"
    assert v.source_id == "101"
    assert v.title == "Software Engineer Intern"
    assert v.company_name == "Acme Corp"
    assert v.employment_type == "intern"
    assert v.salary_min == 50000.0
    assert v.salary_max == 70000.0
    assert v.currency == "USD"


@patch("pkl_research.scraper.vacancy_sources.remoteok.fetch_json")
def test_remoteok_parser(mock_fetch):
    mock_fetch.return_value = [
        {"legal": "disclaimer"},
        {
            "id": "202",
            "position": "AI Engineer (Freelance)",
            "company": "AI Labs",
            "location": "Remote",
            "description": "Build RAG systems",
            "tags": ["python", "ai"],
            "salary_min": 120000,
            "salary_max": 150000,
            "date": "2026-08-10T12:00:00Z",
            "url": "http://example.com/job2",
        }
    ]
    src = RemoteokSource()
    res = src.fetch("ai", limit=10)
    assert len(res) == 1
    v = res[0]
    assert v.source == "remoteok"
    assert v.source_id == "202"
    assert v.employment_type == "freelance"
    assert v.salary_min == 120000.0
    assert v.salary_max == 150000.0


@patch("pkl_research.scraper.vacancy_sources.himalayas.fetch_json")
def test_himalayas_parser(mock_fetch):
    mock_fetch.return_value = {
        "jobs": [
            {
                "id": "303",
                "title": "Fullstack Contract Developer",
                "companyName": "Vercel",
                "location": "Remote",
                "categories": ["React", "Node"],
                "salaryMin": 90000,
                "salaryMax": 100000,
                "pubDate": "2026-08-10T12:00:00Z",
                "applicationLink": "http://example.com/job3",
                "description": "Fullstack developer role",
            }
        ]
    }
    src = HimalayasSource()
    res = src.fetch("fullstack", limit=10)
    assert len(res) == 1
    v = res[0]
    assert v.source == "himalayas"
    assert v.source_id == "303"
    assert v.employment_type == "contract"


@patch("pkl_research.scraper.vacancy_sources.wwr.fetch_url")
def test_wwr_parser(mock_fetch):
    mock_fetch.return_value = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>WWR Company: Junior Game Developer</title>
          <link>http://example.com/job4</link>
          <guid>404</guid>
          <description>Build Godot games</description>
          <pubDate>Mon, 10 Aug 2026 12:00:00 +0000</pubDate>
          <category>Godot</category>
        </item>
      </channel>
    </rss>
    """
    src = WwrSource()
    res = src.fetch("game", limit=10)
    assert len(res) == 1
    v = res[0]
    assert v.source == "wwr"
    assert v.source_id == "404"
    assert v.company_name == "WWR Company"
    assert v.title == "Junior Game Developer"


@patch("pkl_research.scraper.vacancy_sources.greenhouse.fetch_json")
def test_greenhouse_parser(mock_fetch):
    mock_fetch.return_value = {
        "jobs": [
            {
                "id": 505,
                "title": "AI Research Assistant",
                "content": "Deep learning research",
                "location": {"name": "Remote, US"},
                "absolute_url": "http://example.com/job5",
                "updated_at": "2026-08-10T12:00:00Z",
            }
        ]
    }
    src = GreenhouseSource()
    res = src.fetch("research", limit=10, board_token="openai")
    assert len(res) == 1
    v = res[0]
    assert v.source == "greenhouse"
    assert v.source_id == "openai:505"
    assert v.company_name == "Openai"


@patch("pkl_research.scraper.vacancy_sources.lever.fetch_json")
def test_lever_parser(mock_fetch):
    mock_fetch.return_value = [
        {
            "id": "606",
            "title": "Fullstack Web Intern",
            "description": "React/Node web app development",
            "categories": {
                "location": "Remote, Europe",
                "commitment": "Internship",
            },
            "createdAt": 1786377600000, # Aug 10 2026
            "hostedUrl": "http://example.com/job6",
        }
    ]
    src = LeverSource()
    res = src.fetch("web", limit=10, board_token="deliveroo")
    assert len(res) == 1
    v = res[0]
    assert v.source == "lever"
    assert v.source_id == "deliveroo:606"
    assert v.employment_type == "intern"


@patch("pkl_research.scraper.vacancy_sources.ashby.fetch_json")
def test_ashby_parser(mock_fetch):
    mock_fetch.return_value = {
        "jobs": [
            {
                "id": "707",
                "title": "Game Developer Intern",
                "jobDescriptionPlain": "Unity gameplay developer",
                "location": "Remote",
                "employmentType": "Internship",
                "publishedAt": "2026-08-10T12:00:00Z",
                "infoUrl": "http://example.com/job7",
            }
        ]
    }
    src = AshbySource()
    res = src.fetch("game", limit=10, board_token="vercel")
    assert len(res) == 1
    v = res[0]
    assert v.source == "ashby"
    assert v.source_id == "vercel:707"
    assert v.employment_type == "intern"
