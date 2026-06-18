import json
import logging
import os
import hashlib
from anthropic import Anthropic

logger = logging.getLogger(__name__)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SEARCH_SYSTEM_PROMPT = """You are a job listing extractor. When given a search task, 
use your web_search tool to find current job listings matching the criteria.
Return ONLY a valid JSON array of job objects with these fields:
- title (string)
- company (string, empty string if unknown)
- url (string, direct link to job posting)
- location (string)
- description (string, brief summary max 300 chars)
- work_mode (string: "remote", "hybrid", "onsite", or "unknown")
- salary (string, empty if not listed)
- posted_at (string, ISO date or empty)
- tags (array of strings, detected tech keywords)

Return ONLY the JSON array, no explanation, no markdown, no backticks."""


def fetch_via_claude_search(source: dict, profiles: list[dict]) -> list[dict]:
    """Use Claude with web_search to find jobs on a given site."""
    enabled_profiles = [p for p in profiles if p.get("enabled", True)]
    if not enabled_profiles:
        return []

    all_keywords = []
    for profile in enabled_profiles:
        keywords = profile.get("keywords", [])
        if isinstance(keywords, str):
            keywords = json.loads(keywords)
        all_keywords.extend(keywords)

    keyword_str_en = " OR ".join(
        f'"{kw}"' for kw in all_keywords if not any(
            c in kw for c in "áéíóúñü"
        )
    )
    keyword_str_es = " OR ".join(
        f'"{kw}"' for kw in all_keywords if any(
            c in kw for c in "áéíóúñü"
        ) or kw in ("devops", "sysadmin", "linux")
    )

    base_url = source["base_url"]
    site_name = source["name"]

    prompts = []
    if keyword_str_en:
        prompts.append(
            f"Search for current job listings on {base_url} for: {keyword_str_en}. "
            f"Focus on remote and hybrid positions. Return as JSON array."
        )
    if keyword_str_es:
        prompts.append(
            f"Busca ofertas de trabajo actuales en {base_url} para: {keyword_str_es}. "
            f"Prioriza posiciones remotas e híbridas. Devuelve como JSON array."
        )

    all_jobs = []
    for prompt in prompts:
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=SEARCH_SYSTEM_PROMPT,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )

            raw_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    raw_text += block.text

            if not raw_text.strip():
                continue

            clean = raw_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()

            jobs_raw = json.loads(clean)
            if not isinstance(jobs_raw, list):
                continue

            for job in jobs_raw:
                if not job.get("title") or not job.get("url"):
                    continue
                job["source"] = site_name
                job["external_id"] = hashlib.md5(
                    f"{site_name}:{job['url']}".encode()
                ).hexdigest()
                if isinstance(job.get("tags"), list):
                    job["tags"] = json.dumps(job["tags"])
                else:
                    job["tags"] = "[]"
                all_jobs.append(job)

        except json.JSONDecodeError as e:
            logger.warning(f"[Search] {site_name}: JSON parse error — {e}")
        except Exception as e:
            logger.error(f"[Search] {site_name}: Error — {e}")

    # Deduplicate by external_id
    seen = set()
    unique = []
    for job in all_jobs:
        if job["external_id"] not in seen:
            seen.add(job["external_id"])
            unique.append(job)

    logger.info(f"[Search] {site_name}: {len(unique)} jobs found")
    return unique
