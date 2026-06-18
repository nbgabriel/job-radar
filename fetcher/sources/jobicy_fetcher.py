import requests
import hashlib
import json
import logging
from sources.rss_fetcher import job_matches_profiles, extract_tags, detect_work_mode

logger = logging.getLogger(__name__)

JOBICY_API = "https://jobicy.com/api/v2/remote-jobs"

QUERIES = [
    {"tag": "devops", "count": 50},
    {"tag": "sysadmin", "count": 50},
    {"tag": "linux", "count": 50},
    {"tag": "infrastructure engineer", "count": 50},
    {"tag": "automation engineer", "count": 50},
]

def fetch_jobicy(profiles=None):
    jobs = []
    seen = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; JobRadar/1.0)"
    }

    for params in QUERIES:
        try:
            r = requests.get(JOBICY_API, params=params, headers=headers, timeout=10)
            if r.status_code != 200:
                logger.warning(f"[Jobicy] HTTP {r.status_code} for tag={params['tag']}")
                continue

            data = r.json()
            if not data.get("success", True) and "error" in data:
                logger.warning(f"[Jobicy] API error: {data['error']}")
                continue

            raw_jobs = data.get("jobs", [])
            for j in raw_jobs:
                url = j.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)

                title = j.get("jobTitle", "")
                company = j.get("companyName", "")
                description = j.get("jobDescription", "") or j.get("jobExcerpt", "")
                full_text = f"{title} {description}"

                job = {
                    "external_id": hashlib.md5(f"jobicy:{url}".encode()).hexdigest(),
                    "title": title,
                    "company": company,
                    "url": url,
                    "source": "Jobicy",
                    "description": description[:2000],
                    "tags": json.dumps(extract_tags(full_text)),
                    "work_mode": detect_work_mode(full_text),
                    "salary": _salary(j),
                    "location": j.get("jobGeo", ""),
                    "posted_at": j.get("pubDate", ""),
                }
                jobs.append(job)

        except Exception as e:
            logger.error(f"[Jobicy] Error tag={params['tag']}: {e}")

    if profiles:
        before = len(jobs)
        jobs = [j for j in jobs if job_matches_profiles(j, profiles)]
        logger.info(f"[Jobicy] {len(jobs)}/{before} jobs matched profiles")
    else:
        logger.info(f"[Jobicy] {len(jobs)} jobs fetched")

    return jobs


def _salary(j):
    min_s = j.get("annualSalaryMin") or j.get("salaryMin")
    max_s = j.get("annualSalaryMax") or j.get("salaryMax")
    cur = j.get("salaryCurrency", "USD")
    if min_s and max_s:
        return f"{cur} {int(min_s):,} – {int(max_s):,}"
    if min_s:
        return f"{cur} {int(min_s):,}+"
    return ""
