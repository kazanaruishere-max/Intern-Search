from pkl_research import config


def test_load_vacancy_sources():
    sources = config.load_vacancy_sources()
    assert isinstance(sources, dict)
    assert "aggregators" in sources
    assert "corporate_boards" in sources
