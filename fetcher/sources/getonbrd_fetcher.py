"""
GetOnBrd fetcher — scrapes job listings using Playwright + stealth mode.

The RSS feed configured in config.yaml (getonbrd.com/jobs.rss) consistently
returns 0 results, so this scrapes the search results page directly instead.
GetOnBrd shows all results on a single page (no pagination needed for a
single query), which keeps this simpler than Bumeran/Computrabajo.

Listings live in <a class="results-item ..."> blocks with title, company,
location, and posted date all inline -- no JSON-LD on this site. Unlike
Bumeran/Computrabajo, we do NOT do a second page load per job here: the
listing page already has everything needed (title, company, location,
work mode, posted date, direct link). Clicking through from the dashboard
takes the user straight to GetOnBrd for the full description.
"""

import re
import json
import hashlib
import logging
import time

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.getonbrd.com/jobs-{query}"
BASE_URL = "https://www.getonbrd.com"

DEFAULT_QUERIES = ["devops", "sysadmin-devops-qa"]


def _extract_listings(html: str) -> list[dict]:
    """Parse <a class="results-item ..."> blocks from the search results page."""
    # Each listing is an <a ...>...</a> block; split on the opening tag to
    # isolate individual cards, since results-item blocks aren't nested.
    cards = re.split(r'(?=<a class="results-item)', html)

    listings = []
    seen_urls = set()

    for card in cards:
        href_match = re.search(r'<a class="results-item[^"]*"[^>]*href="([^"]+)"', card)
        if not href_match:
            continue

        url = href_match.group(1)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title_match = re.search(
            r'<h4 class="results-list-title">.*?<strong[^>]*>(?:<i[^>]*></i>)?([^<]+)</strong>',
            card,
            re.DOTALL,
        )
        title = title_match.group(1).strip() if title_match else ""
        if not title:
            continue

        company_match = re.search(
            r'class="results-list-info">.*?<strong>([^<]+)</strong>', card, re.DOTALL
        )
        company = company_match.group(1).strip() if company_match else ""

        location_match = re.search(
            r'<span class="location">\s*(?:<span[^>]*>)?\s*(?:<i[^>]*></i>)?\s*([^<\n]+)',
            card,
            re.DOTALL,
        )
        location = location_match.group(1).strip() if location_match else ""

        work_mode = ""
        if "icon-wifi" in card or location.lower() == "remote":
            work_mode = "Remoto"
        elif "perk-remote_full" in card:
            work_mode = "Remoto"
        elif location:
            work_mode = "Presencial"

        posted_match = re.search(
            r'<div class="opacity-half size0">\s*([^<]+?)\s*</div>', card
        )
        posted_at = posted_match.group(1).strip() if posted_match else ""

        listings.append(
            {
                "title": title,
                "url": url if url.startswith("http") else BASE_URL + url,
                "company": company,
                "location": location,
                "work_mode": work_mode,
                "posted_at": posted_at,
            }
        )

    return listings


def _extract_detail_description(html: str) -> str:
    """Pull the full description text from an individual job posting page.

    GetOnBrd marks the whole job body with itemprop="description" (schema.org
    microdata) inside <div id="job-body">. This wraps several sub-sections
    (company blurb, "Funciones", "Requisitos y perfil", etc.) -- we grab the
    whole block and strip tags rather than trying to isolate one paragraph,
    since the structure varies per posting.
    """
    match = re.search(
        r'<div id="job-body" itemprop="description">(.*?)</div>\s*</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )
    if not match:
        return ""

    raw = match.group(1)
    text = re.sub(r"<br\s*/?>", " ", raw)
    text = re.sub(r"<li>", " - ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_getonbrd(queries: list[str] | None = None, profiles=None, max_per_query: int = 100):
    """Scrape GetOnBrd for the given search queries.

    Only does a single page load per query (the search results page) --
    no per-job detail fetch, since title/company/location/date/link is
    all that's needed. Clicking through takes the user to GetOnBrd directly.
    """
    queries = queries or DEFAULT_QUERIES
    jobs = []
    seen_urls = set()

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for query in queries:
            url = SEARCH_URL.format(query=query)
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)
                html = page.content()
            except Exception as e:
                logger.warning(f"[GetOnBrd] Failed to load search '{query}': {e}")
                continue

            listings = _extract_listings(html)
            logger.info(f"[GetOnBrd] '{query}': {len(listings)} listings found")

            for listing in listings[:max_per_query]:
                full_url = listing["url"]
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                job = {
                    "external_id": hashlib.md5(f"getonbrd:{full_url}".encode()).hexdigest(),
                    "title": listing["title"],
                    "company": listing["company"],
                    "url": full_url,
                    "source": "GetOnBrd",
                    "description": "",
                    "tags": json.dumps([]),
                    "work_mode": listing["work_mode"],
                    "salary": "",
                    "location": listing["location"],
                    "posted_at": listing["posted_at"],
                }
                jobs.append(job)

        browser.close()

    if profiles:
        from sources.rss_fetcher import job_matches_profiles, extract_tags, detect_work_mode

        for job in jobs:
            full_text = f"{job['title']} {job['description']}"
            job["tags"] = json.dumps(extract_tags(full_text))
            if not job["work_mode"]:
                job["work_mode"] = detect_work_mode(full_text)

        before = len(jobs)
        jobs = [j for j in jobs if job_matches_profiles(j, profiles)]
        logger.info(f"[GetOnBrd] {len(jobs)}/{before} jobs matched profiles")

    return jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_getonbrd(queries=["devops"])
    print(f"\nFound {len(results)} jobs:\n")
    for j in results:
        print(f"- {j['title']} @ {j['company']} ({j['location']}, {j['work_mode']})")
        print(f"  {j['url']}")
        print(f"  {j['description'][:150]}...\n")
