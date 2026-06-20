"""
Computrabajo fetcher — scrapes job listings using Playwright + stealth mode.

Unlike Bumeran/Zonajobs, Computrabajo doesn't appear to need Cloudflare
bypass (stealth works but may not even be required) and has no JSON-LD
JobPosting markup. Listings are extracted from <article class="box_offer">
blocks using utility CSS classes, which are more stable than the hashed
styled-components classes Bumeran uses.

Computrabajo also lists the same offer multiple times with different
data-id values (likely internal tracking/placement variants), so dedup is
done by URL slug (stripping the trailing hash) rather than by full URL.
"""

import re
import json
import hashlib
import logging
import time

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

SEARCH_URL = "https://ar.computrabajo.com/trabajo-de-{query}"
BASE_URL = "https://ar.computrabajo.com"

DEFAULT_QUERIES = ["devops", "sysadmin-linux", "infraestructura"]

# Strips the trailing 32-char hex ID + #lc=... fragment so duplicate
# placements of the same offer collapse to one slug.
_SLUG_RE = re.compile(r"-[A-F0-9]{32}(#.*)?$")


def _slug_for(href: str) -> str:
    return _SLUG_RE.sub("", href)


def _extract_listings(html: str) -> list[dict]:
    """Parse <article class="box_offer"> blocks from the search results page."""
    articles = re.findall(
        r'<article class="box_offer[^"]*"[^>]*>(.*?)</article>',
        html,
        re.DOTALL,
    )

    listings = []
    seen_slugs = set()

    for block in articles:
        link_match = re.search(
            r'<a class="js-o-link[^"]*"\s+href="([^"]+)">\s*([^<]+)\s*</a>',
            block,
        )
        if not link_match:
            continue

        href, title = link_match.group(1), link_match.group(2).strip()
        slug = _slug_for(href)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        full_url = href if href.startswith("http") else BASE_URL + href

        company_match = re.search(
            r'offer-grid-article-company-url="">\s*([^<]+)\s*</a>', block
        )
        company = company_match.group(1).strip() if company_match else ""

        location_match = re.search(
            r'<p class="fs16 fc_base mt5">\s*<span class="mr10">\s*([^<]+)\s*</span>',
            block,
        )
        location = location_match.group(1).strip() if location_match else ""

        mode = ""
        if "Presencial y remoto" in block:
            mode = "Híbrido"
        elif "Remoto" in block:
            mode = "Remoto"
        elif "Presencial" in block:
            mode = "Presencial"

        salary_match = re.search(r'\$\s*[\d.,]+(?:\s*\(Mensual\))?', block)
        salary = salary_match.group(0).strip() if salary_match else ""

        listings.append(
            {
                "title": title,
                "url": full_url,
                "company": company,
                "location": location,
                "work_mode": mode,
                "salary": salary,
            }
        )

    return listings


def _extract_detail_description(html: str) -> str:
    """Pull the full description text from an individual offer page.

    The description lives right after an <h3>Descripción de la oferta</h3>
    heading, in a <p class="mbB"> block. There are usually multiple
    <p class="mbB"> tags on the page (salary tags, requirements, etc.) so
    we anchor specifically on the one following that heading.
    """
    match = re.search(
        r'Descripci[oó]n de la oferta</h3>.*?<p class="mbB">(.*?)</p>',
        html,
        re.DOTALL,
    )
    if not match:
        return ""

    text = re.sub(r"<br\s*/?>", " ", match.group(1))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_computrabajo(queries: list[str] | None = None, profiles=None, max_per_query: int = 20):
    """Scrape Computrabajo for the given search queries."""
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
                logger.warning(f"[Computrabajo] Failed to load search '{query}': {e}")
                continue

            listings = _extract_listings(html)
            logger.info(f"[Computrabajo] '{query}': {len(listings)} unique listings found")

            for listing in listings[:max_per_query]:
                full_url = listing["url"]
                slug = _slug_for(full_url)
                if slug in seen_urls:
                    continue
                seen_urls.add(slug)

                try:
                    page.goto(full_url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(1500)
                    detail_html = page.content()
                    description = _extract_detail_description(detail_html)
                except Exception as e:
                    logger.warning(f"[Computrabajo] Failed to load detail '{full_url}': {e}")
                    description = ""

                job = {
                    "external_id": hashlib.md5(f"computrabajo:{slug}".encode()).hexdigest(),
                    "title": listing["title"],
                    "company": listing["company"],
                    "url": full_url,
                    "source": "Computrabajo",
                    "description": description[:2000],
                    "tags": json.dumps([]),
                    "work_mode": listing["work_mode"],
                    "salary": listing["salary"],
                    "location": listing["location"],
                    "posted_at": "",
                }
                jobs.append(job)

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
        logger.info(f"[Computrabajo] {len(jobs)}/{before} jobs matched profiles")

    return jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_computrabajo(queries=["devops"])
    print(f"\nFound {len(results)} jobs:\n")
    for j in results:
        print(f"- {j['title']} @ {j['company']} ({j['location']}, {j['work_mode']}) {j['salary']}")
        print(f"  {j['url']}")
        print(f"  {j['description'][:150]}...\n")
