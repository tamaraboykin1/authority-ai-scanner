"""Cold lead generation — find businesses with poor websites."""
import re
import json
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse


async def analyze_website_quality(url: str) -> dict:
    """Quick website quality check for outreach prospects."""
    issues = []
    score = 100

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, verify=False) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            html = response.text
            soup = BeautifulSoup(html, "lxml")

            # HTTPS check
            if not url.startswith("https"):
                issues.append("Not using HTTPS")
                score -= 15

            # Title
            title = soup.find("title")
            if not title or not title.get_text().strip():
                issues.append("Missing page title")
                score -= 15

            # Meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if not meta_desc or not meta_desc.get("content", "").strip():
                issues.append("Missing meta description")
                score -= 12

            # Mobile viewport
            viewport = soup.find("meta", attrs={"name": "viewport"})
            if not viewport:
                issues.append("Not mobile-optimized")
                score -= 12

            # Schema markup
            schemas = soup.find_all("script", {"type": "application/ld+json"})
            if not schemas:
                issues.append("No structured data")
                score -= 15

            # H1
            h1 = soup.find_all("h1")
            if not h1:
                issues.append("Missing H1 heading")
                score -= 10

            # Images without alt
            images = soup.find_all("img")
            no_alt = [img for img in images if not img.get("alt")]
            if images and len(no_alt) > len(images) * 0.5:
                issues.append(f"{len(no_alt)}/{len(images)} images missing alt text")
                score -= 5

            # Content length
            text = soup.get_text(separator=" ", strip=True)
            word_count = len(text.split())
            if word_count < 200:
                issues.append("Very thin content")
                score -= 10

            # Contact info
            has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text))
            has_email = bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))

            # Extract contact info
            emails_found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            phones_found = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)

            return {
                "url": url,
                "score": max(0, score),
                "issues": issues,
                "issue_count": len(issues),
                "emails_found": list(set(emails_found))[:3],
                "phones_found": list(set(phones_found))[:3],
                "title": title.get_text().strip() if title else "",
                "word_count": word_count,
                "has_ssl": url.startswith("https"),
                "has_mobile": bool(viewport),
                "has_schema": bool(schemas),
                "success": True
            }

    except Exception as e:
        return {
            "url": url,
            "score": 0,
            "issues": ["Website unreachable or error loading"],
            "issue_count": 1,
            "emails_found": [],
            "phones_found": [],
            "title": "",
            "word_count": 0,
            "has_ssl": False,
            "has_mobile": False,
            "has_schema": False,
            "success": False,
            "error": str(e)
        }


async def scan_prospect_websites(websites: list[dict]) -> list[dict]:
    """Scan multiple websites and return quality scores.
    
    Input: [{"business_name": "...", "website_url": "...", "city": "...", "state": "...", "industry": "..."}]
    """
    results = []
    for entry in websites:
        url = entry.get("website_url", "")
        if not url:
            continue
        if not url.startswith("http"):
            url = "https://" + url

        analysis = await analyze_website_quality(url)
        results.append({
            "business_name": entry.get("business_name", ""),
            "website_url": url,
            "city": entry.get("city", ""),
            "state": entry.get("state", ""),
            "industry": entry.get("industry", ""),
            "website_score": analysis["score"],
            "issues": analysis["issues"],
            "email": analysis["emails_found"][0] if analysis["emails_found"] else entry.get("email", ""),
            "phone": analysis["phones_found"][0] if analysis["phones_found"] else entry.get("phone", ""),
            "analysis": analysis
        })

    # Sort by score (worst first — best outreach targets)
    results.sort(key=lambda x: x["website_score"])
    return results
