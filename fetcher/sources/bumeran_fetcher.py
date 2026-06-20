"""
Bumeran fetcher — scrapes job listings using Playwright + stealth mode.

Bumeran is a React SPA protected by Cloudflare. Plain requests/BeautifulSoup
and vanilla Playwright both get blocked (Cloudflare challenge page).
playwright-stealth masks the headless browser fingerprint enough to pass.

Two-step scrape:
  1. Load the search results page, extract the JSON-LD ItemList (title + URL
     for every listing — this is the most reliable source since it's
     structured data Bumeran provides for SEO).
  2. Visit each individual job URL to pull the full description, location,
     work mode, and company name from the rendered page.

This is slower than RSS (N+1 page loads) so it should run on its own
schedule, separate from the lightweight RSS/API fetchers.
"""

import json
import re
import hashlib
import logging
import time

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.bumeran.com.ar/empleos-busqueda-{query}.html"
BASE_URL = "https://www.bumeran.com.ar"

DEFAULT_QUERIES = ["devops", "sre", "sysadmin-linux", "infraestructura"]


def _extract_json_ld_listings(html: str) -> list[dict]:
    """Pull title + url pairs out of the JSON-LD ItemList block.

    Iterates every <script type="application/ld+json"> block on the page
    (there are usually several -- BreadcrumbList, ItemList, etc.) and parses
    whichever one is valid JSON and contains an ItemList.
    """
    blocks = re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )

    listings = []
    for block in blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue

        if data.get("@type") != "ItemList":
            continue

        items = data.get("itemListElement", [])
        for item in items:
            if isinstance(item, list):
                item = item[0] if item else {}
            listing_item = item.get("item", item)
            name = listing_item.get("name")
            url = listing_item.get("url")
            if name and url:
                listings.append({"title": name, "url": url})

        if listings:
            break

    if not listings:
        logger.warning("[Bumeran] No ItemList JSON-LD block found/parsed")

    return listings


def _extract_detail_fields(html: str) -> dict:
    """Extract company, location, work mode, description, posted date from a
    single job posting page using its embedded JobPosting JSON-LD block.

    This is far more reliable than scraping styled-components CSS classes
    (those hashes change on every Bumeran frontend build). The JobPosting
    schema is standard schema.org markup Bumeran provides for SEO/Google
    Jobs indexing, so it's a stable contract.
    """
    result = {
        "company": "",
        "location": "",
        "work_mode": "",
        "description": "",
        "posted_at": "",
    }

    blocks = re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )

    data = None
    for block in blocks:
        try:
            candidate = json.loads(block)
        except json.JSONDecodeError:
            continue
        if candidate.get("@type") == "JobPosting":
            data = candidate
            break

    if not data:
        logger.warning("[Bumeran] No JobPosting JSON-LD found on detail page")
        return result

    # Company
    org = data.get("hiringOrganization", {})
    result["company"] = org.get("name", "")

    # Location
    job_loc = data.get("jobLocation", {})
    address = job_loc.get("address", {}) if isinstance(job_loc, dict) else {}
    locality = address.get("addressLocality", "")
    region = address.get("addressRegion", "")
    result["location"] = ", ".join(p for p in [locality, region] if p)

    # Work mode — TELECOMMUTE means remote in schema.org JobPosting vocab
    if data.get("jobLocationType") == "TELECOMMUTE":
        result["work_mode"] = "Remoto"
    elif result["location"]:
        result["work_mode"] = "Presencial"

    # Description — comes as raw HTML, strip tags and collapse whitespace
    raw_desc = data.get("description", "")
    text = re.sub(r"<[^>]+>", " ", raw_desc)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    result["description"] = text

    result["posted_at"] = data.get("datePosted", "")

    return result


def fetch_bumeran(queries: list[str] | None = None, profiles=None, max_per_query: int = 20):
    """
    Scrape Bumeran for the given search queries.

    Returns a list of job dicts compatible with the job-radar DB schema.
    """
    queries = queries or DEFAULT_QUERIES
    jobs = []
    seen_urls = set()
    seen_content = set()  # (title, company) pairs -- catches cross-posted duplicates (e.g. Zonajobs mirror listings)

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
                logger.warning(f"[Bumeran] Failed to load search '{query}': {e}")
                continue

            listings = _extract_json_ld_listings(html)
            logger.info(f"[Bumeran] '{query}': {len(listings)} listings found")

            for listing in listings[:max_per_query]:
                full_url = listing["url"]
                if not full_url.startswith("http"):
                    full_url = BASE_URL + full_url

                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                try:
                    page.goto(full_url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(1500)
                    detail_html = page.content()
                    details = _extract_detail_fields(detail_html)
                except Exception as e:
                    logger.warning(f"[Bumeran] Failed to load detail '{full_url}': {e}")
                    details = {"company": "", "location": "", "work_mode": "", "description": ""}

                content_key = (listing["title"].strip().lower(), details["company"].strip().lower())
                if content_key in seen_content:
                    logger.info(f"[Bumeran] Skipping cross-posted duplicate: {listing['title']}")
                    continue
                seen_content.add(content_key)

                job = {
                    "external_id": hashlib.md5(f"bumeran:{full_url}".encode()).hexdigest(),
                    "title": listing["title"],
                    "company": details["company"],
                    "url": full_url,
                    "source": "Bumeran",
                    "description": details["description"][:2000],
                    "tags": json.dumps([]),
                    "work_mode": details["work_mode"],
                    "salary": "",
                    "location": details["location"],
                    "posted_at": details["posted_at"],
                }
                jobs.append(job)

                # Be polite — don't hammer the site
                time.sleep(1)

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
        logger.info(f"[Bumeran] {len(jobs)}/{before} jobs matched profiles")

    return jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_bumeran(queries=["devops"])
    print(f"\nFound {len(results)} jobs:\n")
    for j in results:
        print(f"- {j['title']} @ {j['company']} ({j['location']}, {j['work_mode']})")
        print(f"  {j['url']}")
        print(f"  {j['description'][:150]}...\n")