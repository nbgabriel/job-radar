import feedparser
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

WORK_MODE_HINTS = {
    "remote": ["remote", "remoto", "100% remote", "fully remote", "trabajo remoto"],
    "hybrid": ["hybrid", "híbrido", "hibrido", "mixed"],
    "onsite": ["on-site", "onsite", "presencial", "in-office"],
}

TECH_TAGS = [
    "ansible", "terraform", "docker", "kubernetes", "k8s", "jenkins", "gitlab",
    "github actions", "aws", "azure", "gcp", "linux", "python", "bash", "git",
    "ci/cd", "devops", "sre", "monitoring", "zabbix", "prometheus", "grafana",
    "vault", "cyberark", "vmware", "nginx", "postgresql", "redis", "elk",
    "datadog", "splunk", "airflow", "helm", "argocd", "pulumi",
]



def job_matches_profiles(job: dict, profiles: list[dict]) -> bool:
    """Return True if the job title or description matches any enabled profile keyword."""
    if not profiles:
        return True  # no profiles = show everything
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    for profile in profiles:
        if not profile.get('enabled', True):
            continue
        keywords = profile.get('keywords', [])
        if isinstance(keywords, str):
            import json
            keywords = json.loads(keywords)
        if any(kw.lower() in text for kw in keywords):
            return True
    return False

def detect_work_mode(text: str) -> str:
    text_lower = text.lower()
    for mode, hints in WORK_MODE_HINTS.items():
        if any(h in text_lower for h in hints):
            return mode
    return "unknown"


def extract_tags(text: str) -> list[str]:
    text_lower = text.lower()
    return [tag for tag in TECH_TAGS if tag in text_lower]


def make_external_id(source: str, url: str) -> str:
    return hashlib.md5(f"{source}:{url}".encode()).hexdigest()


def parse_date(entry) -> Optional[str]:
    for attr in ("published", "updated", "created"):
        val = getattr(entry, attr, None)
        if val:
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(val).isoformat()
            except Exception:
                return val
    return None


def fetch_rss(source: dict, profiles: list[dict] = None) -> list[dict]:
    """Fetch jobs from an RSS feed source."""
    jobs = []
    try:
        feed = feedparser.parse(source["url"])
        if feed.bozo and not feed.entries:
            logger.warning(f"[RSS] Failed to parse {source['name']}: {feed.bozo_exception}")
            return []

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            if not title or not url:
                continue

            description = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
            full_text = f"{title} {description}"
            company = (
                entry.get("author", "")
                or entry.get("company", "")
                or _extract_company_from_title(title)
            )

            jobs.append({
                "external_id": make_external_id(source["name"], url),
                "title": title,
                "company": company,
                "url": url,
                "source": source["name"],
                "description": description[:2000],
                "tags": json.dumps(extract_tags(full_text)),
                "work_mode": detect_work_mode(full_text),
                "posted_at": parse_date(entry),
                "location": entry.get("location", ""),
            })

        if profiles:
            before = len(jobs)
            jobs = [j for j in jobs if job_matches_profiles(j, profiles)]
            logger.info(f"[RSS] {source['name']}: {len(jobs)}/{before} jobs matched profiles")
        else:
            logger.info(f"[RSS] {source['name']}: {len(jobs)} jobs fetched")
    except Exception as e:
        logger.error(f"[RSS] Error fetching {source['name']}: {e}")

    return jobs


def _extract_company_from_title(title: str) -> str:
    """Try to extract company from patterns like 'Role at Company' or 'Company - Role'."""
    if " at " in title:
        return title.split(" at ")[-1].strip()
    if " - " in title:
        parts = title.split(" - ")
        if len(parts) >= 2:
            return parts[-1].strip()
    return ""
