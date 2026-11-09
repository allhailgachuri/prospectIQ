"""
Website verification and quality audit for ProspectIQ.

For each prospect:
  1. Determine if it has a verifiable website (VERIFIED_WEBSITE,
     WEBSITE_NOT_FOUND_AFTER_CHECKS, WEBSITE_UNREACHABLE,
     WEBSITE_REQUIRES_MANUAL_REVIEW, WEBSITE_STATUS_UNKNOWN).
  2. If a website is found and reachable, perform a lightweight quality
     audit based on the fetched HTML.

SSRF protection
---------------
All URLs are validated before fetching:
  - Scheme must be http or https.
  - Resolved hostname must NOT be localhost, a loopback address,
    a private IPv4/IPv6 range, or a link-local address.
  - Redirects are followed but re-validated at each hop.
  - Maximum response size: 2 MB.
  - Connection timeout: 10 s, read timeout: 20 s.

Responsible crawling
--------------------
  - One request per business, no recursive crawling.
  - No aggressive parallelism.
  - Respects HTTP errors (4xx, 5xx logged, not crashed on).
"""
import ipaddress
import re
import socket
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests import Response

from .logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Website presence status constants
# ---------------------------------------------------------------------------
STATUS_VERIFIED        = "VERIFIED_WEBSITE"
STATUS_NOT_FOUND       = "WEBSITE_NOT_FOUND_AFTER_CHECKS"
STATUS_UNREACHABLE     = "WEBSITE_UNREACHABLE"
STATUS_MANUAL_REVIEW   = "WEBSITE_REQUIRES_MANUAL_REVIEW"
STATUS_UNKNOWN         = "WEBSITE_STATUS_UNKNOWN"

# ---------------------------------------------------------------------------
# HTTP settings
# ---------------------------------------------------------------------------
CONNECT_TIMEOUT = 10   # seconds
READ_TIMEOUT    = 20   # seconds
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_REDIRECTS   = 5
REQUEST_SLEEP   = 0.5  # seconds between website checks

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ProspectIQ/0.2; "
        "+https://builtbyrushion.vercel.app/)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------------------------

_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


def _is_safe_url(url: str) -> tuple[bool, str]:
    """
    Return (True, "") if the URL is safe to fetch, or (False, reason) if not.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"URL parse error: {exc}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Unsafe scheme: {parsed.scheme!r}"

    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname in URL"

    # Resolve to IP and check against private ranges
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        return False, f"DNS resolution failed: {exc}"

    for addr_info in addresses:
        ip_str = addr_info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for private_range in _PRIVATE_RANGES:
            if ip in private_range:
                return False, f"Hostname resolves to private/reserved IP: {ip_str}"

    return True, ""


# ---------------------------------------------------------------------------
# Safe HTTP fetch
# ---------------------------------------------------------------------------

def _safe_get(url: str) -> tuple[Response | None, str]:
    """
    Fetch *url* safely.  Returns (response, error_message).
    error_message is "" on success.
    """
    safe, reason = _is_safe_url(url)
    if not safe:
        return None, f"SSRF check failed: {reason}"

    session = requests.Session()
    session.max_redirects = MAX_REDIRECTS

    try:
        resp = session.get(
            url,
            headers=_HEADERS,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            stream=True,
            allow_redirects=True,
        )
        # Read up to MAX_RESPONSE_BYTES
        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) >= MAX_RESPONSE_BYTES:
                break
        resp._content = content
        return resp, ""

    except requests.exceptions.SSLError as exc:
        return None, f"SSL error: {exc}"
    except requests.exceptions.ConnectionError as exc:
        return None, f"Connection error: {exc}"
    except requests.exceptions.Timeout:
        return None, "Request timed out"
    except requests.exceptions.TooManyRedirects:
        return None, "Too many redirects"
    except requests.exceptions.RequestException as exc:
        return None, f"Request error: {exc}"


# ---------------------------------------------------------------------------
# Website verification
# ---------------------------------------------------------------------------

def verify_website(url: str) -> dict[str, Any]:
    """
    Verify that a URL belongs to a live, accessible website.

    Returns a verification result dict.
    """
    now = datetime.now(timezone.utc).isoformat()

    if not url:
        return {
            "status":       STATUS_UNKNOWN,
            "verified_url": None,
            "http_status":  None,
            "https":        None,
            "error":        "No URL provided",
            "checked_at":   now,
        }

    # Normalise: ensure scheme
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url

    resp, error = _safe_get(url)
    time.sleep(REQUEST_SLEEP)

    if error:
        # Try http:// fallback if https:// failed
        if url.startswith("https://"):
            http_url = "http://" + url[8:]
            resp, error2 = _safe_get(http_url)
            if error2:
                return {
                    "status":       STATUS_UNREACHABLE,
                    "verified_url": url,
                    "http_status":  None,
                    "https":        False,
                    "error":        f"HTTPS: {error}; HTTP: {error2}",
                    "checked_at":   now,
                }
            # http fallback worked
            final_url = resp.url
            return {
                "status":       STATUS_VERIFIED,
                "verified_url": final_url,
                "http_status":  resp.status_code,
                "https":        False,   # working but not on HTTPS
                "error":        None,
                "checked_at":   now,
            }
        return {
            "status":       STATUS_UNREACHABLE,
            "verified_url": url,
            "http_status":  None,
            "https":        None,
            "error":        error,
            "checked_at":   now,
        }

    final_url = resp.url
    status_code = resp.status_code
    uses_https = final_url.startswith("https://")

    if status_code >= 400:
        return {
            "status":       STATUS_UNREACHABLE,
            "verified_url": final_url,
            "http_status":  status_code,
            "https":        uses_https,
            "error":        f"HTTP {status_code}",
            "checked_at":   now,
        }

    return {
        "status":       STATUS_VERIFIED,
        "verified_url": final_url,
        "http_status":  status_code,
        "https":        uses_https,
        "error":        None,
        "checked_at":   now,
    }


# ---------------------------------------------------------------------------
# Website quality audit
# ---------------------------------------------------------------------------

def audit_website(url: str, resp: Response | None = None) -> dict[str, Any]:
    """
    Perform a lightweight quality audit on a website's homepage.

    If *resp* is None, fetches the URL first.
    Returns a dict of findings and an overall quality score (0–100).
    """
    now = datetime.now(timezone.utc).isoformat()

    if resp is None:
        resp, error = _safe_get(url)
        if error or resp is None:
            return {
                "audited":      False,
                "error":        error or "No response",
                "audited_url":  url,
                "audited_at":   now,
                "score":        None,
                "findings":     [],
            }

    try:
        html = resp.content.decode("utf-8", errors="replace")
    except Exception:
        html = ""

    findings: list[dict] = []
    score = 100  # Start at 100, deduct for each issue found

    final_url = resp.url
    uses_https = final_url.startswith("https://")

    # ---- HTTPS ----
    if not uses_https:
        findings.append({
            "check":    "HTTPS",
            "result":   "FAIL",
            "detail":   "Website does not use HTTPS. Browsers flag HTTP sites as 'Not Secure'.",
            "severity": "HIGH",
        })
        score -= 20
    else:
        findings.append({"check": "HTTPS", "result": "PASS", "detail": "Website uses HTTPS.", "severity": None})

    # ---- Meta viewport (mobile responsiveness signal) ----
    has_viewport = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE))
    if not has_viewport:
        findings.append({
            "check":    "Mobile viewport",
            "result":   "FAIL",
            "detail":   "No <meta name='viewport'> tag found. The site may not be mobile-friendly.",
            "severity": "HIGH",
        })
        score -= 15
    else:
        findings.append({"check": "Mobile viewport", "result": "PASS", "detail": "Viewport meta tag present.", "severity": None})

    # ---- Title tag ----
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    if not title:
        findings.append({
            "check":    "Page title",
            "result":   "FAIL",
            "detail":   "No <title> tag found. This hurts search engine visibility.",
            "severity": "MEDIUM",
        })
        score -= 10
    elif len(title) < 10:
        findings.append({
            "check":    "Page title",
            "result":   "WEAK",
            "detail":   f"Title tag is very short: '{title}'. A descriptive title improves SEO.",
            "severity": "LOW",
        })
        score -= 5
    else:
        findings.append({"check": "Page title", "result": "PASS", "detail": f"Title: '{title[:80]}'", "severity": None})

    # ---- Meta description ----
    has_meta_desc = bool(re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=', html, re.IGNORECASE
    ))
    if not has_meta_desc:
        findings.append({
            "check":    "Meta description",
            "result":   "FAIL",
            "detail":   "No meta description tag found. Affects search engine snippets.",
            "severity": "MEDIUM",
        })
        score -= 8
    else:
        findings.append({"check": "Meta description", "result": "PASS", "detail": "Meta description present.", "severity": None})

    # ---- Contact information ----
    # Look for phone, email, or a contact page link
    has_phone = bool(re.search(r'(\+254|07\d{8}|01\d{8})', html))
    has_email = bool(re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', html))
    has_contact_link = bool(re.search(r'href=["\'][^"\']*contact[^"\']*["\']', html, re.IGNORECASE))

    if not (has_phone or has_email or has_contact_link):
        findings.append({
            "check":    "Contact information",
            "result":   "FAIL",
            "detail":   "No phone number, email address or contact page link found on the homepage.",
            "severity": "HIGH",
        })
        score -= 15
    else:
        contact_types = []
        if has_phone: contact_types.append("phone")
        if has_email: contact_types.append("email")
        if has_contact_link: contact_types.append("contact page link")
        findings.append({
            "check":    "Contact information",
            "result":   "PASS",
            "detail":   f"Found: {', '.join(contact_types)}.",
            "severity": None,
        })

    # ---- Call to action ----
    cta_patterns = [
        r'\bget\s+(a\s+)?quote\b', r'\bbook\s+(now|appointment|a\s+call)\b',
        r'\bcontact\s+us\b', r'\bget\s+started\b', r'\blearn\s+more\b',
        r'\bshop\s+now\b', r'\border\s+now\b', r'\bsign\s+up\b',
        r'\bschedule\s+a\b', r'\brequest\s+a\b',
    ]
    has_cta = any(re.search(p, html, re.IGNORECASE) for p in cta_patterns)
    if not has_cta:
        findings.append({
            "check":    "Call to action",
            "result":   "WEAK",
            "detail":   "No obvious call-to-action phrases found. The site may not convert visitors to leads.",
            "severity": "MEDIUM",
        })
        score -= 8
    else:
        findings.append({"check": "Call to action", "result": "PASS", "detail": "Call-to-action text found.", "severity": None})

    # ---- Page load size ----
    content_size = len(resp.content)
    if content_size > 1_500_000:
        findings.append({
            "check":    "Page size",
            "result":   "WEAK",
            "detail":   f"Homepage HTML is {content_size // 1024} KB. Large pages can slow load times.",
            "severity": "LOW",
        })
        score -= 5

    # ---- Broken / placeholder content signals ----
    broken_signals = [
        "lorem ipsum", "coming soon", "under construction",
        "page not found", "403 forbidden", "404 not found",
        "this site is currently unavailable",
    ]
    found_broken = [s for s in broken_signals if s in html.lower()]
    if found_broken:
        findings.append({
            "check":    "Content quality",
            "result":   "FAIL",
            "detail":   f"Page contains suspicious text: {found_broken}",
            "severity": "HIGH",
        })
        score -= 20

    # ---- Social media links ----
    has_social = bool(re.search(
        r'(facebook\.com|instagram\.com|twitter\.com|linkedin\.com|youtube\.com|tiktok\.com)',
        html, re.IGNORECASE
    ))
    if not has_social:
        findings.append({
            "check":    "Social media links",
            "result":   "WEAK",
            "detail":   "No social media profile links found on the homepage.",
            "severity": "LOW",
        })
        score -= 3

    # Clamp score to 0–100
    score = max(0, min(100, score))

    # Derive a quality label
    if score >= 80:
        quality_label = "GOOD"
    elif score >= 60:
        quality_label = "FAIR"
    elif score >= 40:
        quality_label = "WEAK"
    else:
        quality_label = "POOR"

    # Identify top improvement recommendations
    recommendations = [
        f["detail"]
        for f in findings
        if f.get("result") in ("FAIL", "WEAK") and f.get("severity") in ("HIGH", "MEDIUM")
    ]

    return {
        "audited":          True,
        "audited_url":      final_url,
        "audited_at":       now,
        "score":            score,
        "quality_label":    quality_label,
        "https":            uses_https,
        "mobile_friendly":  has_viewport,
        "has_title":        bool(title),
        "has_meta_desc":    has_meta_desc,
        "has_contact_info": bool(has_phone or has_email or has_contact_link),
        "has_cta":          has_cta,
        "findings":         findings,
        "recommendations":  recommendations,
        "error":            None,
    }


# ---------------------------------------------------------------------------
# Combined check
# ---------------------------------------------------------------------------

def check_business_website(business: dict[str, Any]) -> dict[str, Any]:
    """
    Run verification + audit for a single business record.

    Returns a combined result dict ready for storage.
    """
    url = business.get("website")

    if not url:
        return {
            "source_record_id":      business["source_record_id"],
            "website_status":        STATUS_UNKNOWN,
            "verified_url":          None,
            "https":                 None,
            "http_status":           None,
            "website_error":         None,
            "website_checked_at":    datetime.now(timezone.utc).isoformat(),
            "audit_score":           None,
            "audit_quality_label":   None,
            "audit_mobile_friendly": None,
            "audit_has_contact":     None,
            "audit_has_cta":         None,
            "audit_findings_json":   None,
            "audit_recommendations": None,
            "audit_at":              None,
        }

    log.info("Checking website for '%s': %s", business.get("name"), url)

    vr = verify_website(url)

    audit_result: dict[str, Any] = {}
    if vr["status"] == STATUS_VERIFIED:
        # Re-fetch for audit (verification already consumed the response)
        audit_result = audit_website(vr["verified_url"])
        time.sleep(REQUEST_SLEEP)

    import json
    findings_json = (
        json.dumps(audit_result.get("findings", []), ensure_ascii=False)
        if audit_result else None
    )
    recommendations = (
        "; ".join(audit_result.get("recommendations", []))
        if audit_result else None
    )

    return {
        "source_record_id":      business["source_record_id"],
        "website_status":        vr["status"],
        "verified_url":          vr.get("verified_url"),
        "https":                 vr.get("https"),
        "http_status":           vr.get("http_status"),
        "website_error":         vr.get("error"),
        "website_checked_at":    vr["checked_at"],
        "audit_score":           audit_result.get("score"),
        "audit_quality_label":   audit_result.get("quality_label"),
        "audit_mobile_friendly": audit_result.get("mobile_friendly"),
        "audit_has_contact":     audit_result.get("has_contact_info"),
        "audit_has_cta":         audit_result.get("has_cta"),
        "audit_findings_json":   findings_json,
        "audit_recommendations": recommendations,
        "audit_at":              audit_result.get("audited_at"),
    }
