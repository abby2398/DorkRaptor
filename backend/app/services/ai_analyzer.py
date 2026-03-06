"""
DorkRaptor AI Analysis Service
Uses OpenAI to classify findings and generate risk assessments
"""

import logging
from typing import Dict, Optional, List
import json

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# Plain string rule maps — no enum imports needed
SEVERITY_RULES = {
    "critical": [
        ".env", "aws_secret", "private_key", "database_password", "db_password",
        "BEGIN RSA PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY", "mysqldump",
        "CREATE TABLE", "INSERT INTO", "ext:sql", "ext:env",
        "config.php", "wp-config", "connection_string", "SMTP_PASSWORD",
        "api_key", "access_token", "client_secret", "AKIA", "aws_access_key_id",
    ],
    "high": [
        "admin", "administrator", "phpmyadmin", "cpanel", "inurl:login",
        "swagger", "api/v", "graphql", "ext:log", "ext:bak", "ext:backup",
        "phpinfo", "shell.php", "webshell", "intitle:\"index of\"",
        "directory listing", "backup", "dump",
    ],
    "medium": [
        "filetype:pdf", "filetype:xlsx", "filetype:docx", "inurl:dashboard",
        "inurl:portal", "inurl:dev", "inurl:staging", "inurl:test",
        "inurl:beta", "ext:xml", "ext:yaml", "ext:yml", "inurl:api",
        "robots.txt", "sitemap.xml",
    ],
    "low": [
        "filetype:doc", "inurl:search", "inurl:demo",
        "inurl:preview", "inurl:info",
    ],
}

CATEGORY_RULES = {
    "sensitive_files": ["ext:env", "ext:pem", "ext:key", "ext:sql", "wp-config", "config.php"],
    "admin_panels": ["inurl:admin", "inurl:cpanel", "inurl:phpmyadmin", "inurl:manager"],
    "directory_listings": ["intitle:\"index of\"", "directory listing", "parent directory"],
    "backup_files": ["ext:bak", "ext:backup", "ext:old", "ext:zip", "ext:tar"],
    "config_files": ["ext:config", "ext:conf", "ext:cfg", "ext:ini", "ext:yml", "ext:yaml"],
    "credentials": ["password", "api_key", "secret_key", "access_token", "BEGIN RSA"],
    "documents": ["filetype:pdf", "filetype:doc", "filetype:xlsx", "filetype:csv"],
    "database_dumps": ["ext:sql", "mysqldump", "CREATE TABLE", "INSERT INTO", "ext:db"],
    "cloud_storage": ["s3.amazonaws.com", "blob.core.windows.net", "storage.googleapis.com"],
    "github_leaks": ["github.com"],
    "api_endpoints": ["inurl:api", "inurl:swagger", "inurl:graphql", "inurl:rest"],
}


def classify_finding_local(url: str, dork: str, title: str = "") -> Dict:
    """Rule-based local classification — no API needed"""
    text = f"{url} {dork} {title}".lower()

    severity = "info"
    for sev, keywords in SEVERITY_RULES.items():
        if any(kw.lower() in text for kw in keywords):
            severity = sev
            break

    category = "other"
    for cat, keywords in CATEGORY_RULES.items():
        if any(kw.lower() in text for kw in keywords):
            category = cat
            break

    return {"severity": severity, "category": category}


async def analyze_with_ai(
    findings: List[Dict],
    domain: str,
    api_key: Optional[str] = None,
) -> List[Dict]:
    key = api_key or settings.OPENAI_API_KEY

    if not key or not findings:
        for f in findings:
            result = classify_finding_local(
                f.get("url", ""),
                f.get("dork_query", ""),
                f.get("title", ""),
            )
            f["severity"] = result["severity"]
            f["category"] = result["category"]
            f["ai_explanation"] = generate_local_explanation(f)
        return findings

    batch_size = 10
    for i in range(0, len(findings), batch_size):
        batch = findings[i:i + batch_size]
        await _analyze_batch_openai(batch, domain, key)

    return findings


async def _analyze_batch_openai(findings: List[Dict], domain: str, api_key: str):
    findings_text = "\n".join([
        f"{idx+1}. URL: {f.get('url', 'N/A')}\n   Dork: {f.get('dork_query', 'N/A')}\n   Title: {f.get('title', 'N/A')}"
        for idx, f in enumerate(findings)
    ])

    prompt = f"""You are a cybersecurity expert analyzing OSINT reconnaissance findings for domain: {domain}

Analyze these {len(findings)} findings and for each one provide:
1. severity: CRITICAL/HIGH/MEDIUM/LOW/INFO
2. category: one of sensitive_files/admin_panels/directory_listings/backup_files/config_files/credentials/documents/database_dumps/cloud_storage/github_leaks/api_endpoints/other
3. explanation: 1-2 sentence explanation of the security risk

Findings:
{findings_text}

Respond with ONLY a JSON array: [{{"severity": "...", "category": "...", "explanation": "..."}}]
No other text."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.1,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                analyses = json.loads(content)

                for idx, analysis in enumerate(analyses):
                    if idx < len(findings):
                        findings[idx]["severity"] = analysis.get("severity", "info").lower()
                        findings[idx]["category"] = analysis.get("category", "other").lower()
                        findings[idx]["ai_explanation"] = analysis.get("explanation", "")

    except Exception as e:
        logger.warning(f"OpenAI analysis failed: {e}, falling back to local classification")
        for f in findings:
            result = classify_finding_local(
                f.get("url", ""), f.get("dork_query", ""), f.get("title", "")
            )
            f["severity"] = result["severity"]
            f["category"] = result["category"]
            f["ai_explanation"] = generate_local_explanation(f)


def generate_local_explanation(finding: Dict) -> str:
    severity = finding.get("severity", "info")
    url = finding.get("url", "")

    explanations = {
        "critical": f"Critical security exposure at {url}. May expose credentials, private keys, or database contents leading to immediate compromise.",
        "high": f"High-risk exposure at {url}. Could expose admin interfaces, API endpoints, or backup data to unauthorized parties.",
        "medium": f"Medium-risk finding at {url}. May reveal internal application structure, dev environments, or semi-sensitive documents.",
        "low": f"Low-risk finding at {url}. Publicly accessible resource that may contain organizational information.",
        "info": f"Informational finding at {url}. Asset discovered during reconnaissance for further investigation.",
    }
    return explanations.get(severity, explanations["info"])


async def generate_scan_summary(findings: List[Dict], domain: str, api_key: Optional[str] = None) -> str:
    key = api_key or settings.OPENAI_API_KEY

    critical = sum(1 for f in findings if f.get("severity") == "critical")
    high = sum(1 for f in findings if f.get("severity") == "high")
    medium = sum(1 for f in findings if f.get("severity") == "medium")
    total = len(findings)

    if not key:
        return (
            f"Reconnaissance scan of {domain} completed. "
            f"Discovered {total} total findings: {critical} critical, {high} high, {medium} medium severity. "
            f"{'Immediate attention required for critical findings.' if critical > 0 else 'Review high and medium findings for potential risk.'}"
        )

    prompt = f"""Write a 3-4 sentence executive summary for a recon scan of {domain}.
Stats: {total} total findings, {critical} critical, {high} high, {medium} medium severity.
Be concise, professional, and actionable."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.3,
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"Summary generation failed: {e}")

    return f"Scan of {domain} completed with {total} findings requiring review."
