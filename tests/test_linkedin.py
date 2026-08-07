from pkl_research.scraper.website import _find_social, linkedin_label


def test_linkedin_label():
    assert linkedin_label("https://www.linkedin.com/company/qwords") == "company"
    assert linkedin_label("https://www.linkedin.com/in/nectarwebsite") == "profil pribadi"
    assert linkedin_label("https://www.linkedin.com/school/universitas") == "school"
    assert linkedin_label("https://www.linkedin.com/") == "linkedin"


def test_find_social_filters_external():
    links = {
        "https://nectar.id/",
        "https://nectar.id/tentang/",
        "https://www.linkedin.com/in/nectarwebsite",
        "https://www.instagram.com/nectar_website/",
        "https://github.com/x",
    }
    social = _find_social(links)
    assert any("linkedin" in s for s in social)
    assert any("instagram" in s for s in social)
    assert not any("nectar.id/tentang" in s for s in social)
    assert not any("github.com" in s for s in social)
