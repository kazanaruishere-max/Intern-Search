"""Smoke test enrich (detail + review) untuk satu perusahaan."""

from __future__ import annotations

from pkl_research import config
from pkl_research._compat import setup_utf8_io
from pkl_research.models import Review
from pkl_research.scraper.browser import BrowserSession
from pkl_research.scraper.detail import apply_detail, scrape_detail
from pkl_research.scraper.reviews import open_reviews, parse_reviews, scroll_reviews

setup_utf8_io()

URL = (
    "https://www.google.com/maps/place/Noohtify+-+Software+House+Agency/data=!4m7!"
    "3m6!1s0x2e69f32c58707323:0xc60402cdebe8e989!8m2!3d-6.2342157!4d106.8485929!"
    "16s%2Fg%2F11yx7k118v!19sChIJI3NwWCzzaS4Rieno680CBMY?hl=id"
)


def main(url: str = URL) -> None:
    from pkl_research.models import Company

    company = Company(
        place_id="g/11yx7k118v",
        name="Noohtify",
        maps_url=url,
    )
    with BrowserSession(config.USER_DATA_DIR, headless=True, timeout_ms=30000) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)

        detail = scrape_detail(page)
        updated = apply_detail(company, detail)
        print("=== DETAIL ===")
        print("name:", updated.name)
        print("rating:", updated.rating)
        print("review_count:", updated.review_count)
        print("category:", updated.category)
        print("address:", updated.address)
        print("phone:", updated.phone)
        print("website:", updated.website)
        print("photos:", len(updated.photos))

        if open_reviews(page):
            scroll_reviews(page, max_rounds=10)
            reviews = parse_reviews(page, limit=5)
            for r in reviews:
                r.company_id = 0
            print("=== REVIEWS ===")
            print("jumlah:", len(reviews))
            for r in reviews[:5]:
                print(
                    f"- {r.reviewer_name} [{r.reviewer_rating}] ({r.review_date}): "
                    f"{(r.review_text or '')[:80]}"
                )
        else:
            print("Panel review tidak terbuka")


if __name__ == "__main__":
    import sys

    main(sys.argv[1] if len(sys.argv) > 1 else URL)
