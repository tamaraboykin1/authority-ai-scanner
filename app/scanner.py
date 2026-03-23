import httpx
import os
import re
import json
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from urllib.parse import urlparse

def get_openai_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "")


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith("http://") and not url.startswith("https://"):
        if url.startswith("www."):
            url = "https://" + url
        else:
            url = "https://www." + url
    return url


def grade_from_score(score: int) -> str:
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    return "F"


async def fetch_page(url: str) -> dict:
    """Fetch a webpage and return its HTML content and metadata."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, verify=False) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            return {
                "status_code": response.status_code,
                "html": response.text,
                "url": str(response.url),
                "headers": dict(response.headers),
                "success": True
            }
    except Exception as e:
        return {"success": False, "error": str(e), "html": "", "headers": {}, "status_code": 0, "url": url}


def analyze_seo(html: str, url: str) -> dict:
    """Analyze basic SEO factors."""
    soup = BeautifulSoup(html, "lxml")
    issues = []
    score = 100

    # Title tag
    title = soup.find("title")
    title_text = title.get_text().strip() if title else ""
    if not title_text:
        issues.append({"issue": "Missing page title", "impact": "high", "recommendation": "Add a descriptive <title> tag that includes your business name and location"})
        score -= 15
    elif len(title_text) < 20:
        issues.append({"issue": "Page title too short", "impact": "medium", "recommendation": f"Expand your title from '{title_text}' to include your service and city"})
        score -= 8

    # Meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_text = meta_desc.get("content", "").strip() if meta_desc else ""
    if not desc_text:
        issues.append({"issue": "Missing meta description", "impact": "high", "recommendation": "Add a meta description that summarizes your business, services, and location"})
        score -= 12
    elif len(desc_text) < 50:
        issues.append({"issue": "Meta description too short", "impact": "medium", "recommendation": "Expand your meta description to 120-160 characters for better AI understanding"})
        score -= 6

    # H1 tags
    h1_tags = soup.find_all("h1")
    if not h1_tags:
        issues.append({"issue": "Missing H1 heading", "impact": "high", "recommendation": "Add a clear H1 heading with your business name and primary service"})
        score -= 10

    # Schema markup
    schemas = soup.find_all("script", {"type": "application/ld+json"})
    if not schemas:
        issues.append({"issue": "No structured data (Schema.org)", "impact": "high", "recommendation": "Add LocalBusiness schema markup so AI can understand your business details"})
        score -= 15
    else:
        has_local_business = False
        for s in schemas:
            try:
                data = json.loads(s.string)
                if isinstance(data, dict) and ("LocalBusiness" in str(data.get("@type", "")) or "Organization" in str(data.get("@type", ""))):
                    has_local_business = True
            except Exception:
                pass
        if not has_local_business:
            issues.append({"issue": "No LocalBusiness schema", "impact": "medium", "recommendation": "Add LocalBusiness structured data with your name, address, phone, and hours"})
            score -= 8

    # Images alt text
    images = soup.find_all("img")
    images_without_alt = [img for img in images if not img.get("alt")]
    if images and len(images_without_alt) > len(images) * 0.5:
        issues.append({"issue": f"{len(images_without_alt)} of {len(images)} images missing alt text", "impact": "medium", "recommendation": "Add descriptive alt text to all images for better AI indexing"})
        score -= 5

    # HTTPS check
    parsed = urlparse(url)
    if parsed.scheme != "https":
        issues.append({"issue": "Website not using HTTPS", "impact": "high", "recommendation": "Switch to HTTPS — AI models trust secure sites more"})
        score -= 10

    return {
        "category": "Website SEO",
        "score": max(0, score),
        "issues": issues,
        "recommendations_count": len(issues)
    }


def analyze_content(html: str, business_name: str, city: str, industry: str) -> dict:
    """Analyze content quality for AI visibility."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True).lower()
    issues = []
    score = 100

    # Business name mentions
    if business_name.lower() not in text:
        issues.append({"issue": "Business name not found in page content", "impact": "high", "recommendation": f"Make sure '{business_name}' appears prominently in your page content"})
        score -= 15

    # City/location mentions
    if city.lower() not in text:
        issues.append({"issue": f"City '{city}' not mentioned in content", "impact": "high", "recommendation": f"Add '{city}' to your content so AI knows where you operate"})
        score -= 12

    # Industry/service mentions
    if industry.lower() not in text:
        issues.append({"issue": f"Industry '{industry}' not clearly mentioned", "impact": "medium", "recommendation": f"Include '{industry}' naturally throughout your content"})
        score -= 8

    # Content length
    word_count = len(text.split())
    if word_count < 200:
        issues.append({"issue": "Very thin content (under 200 words)", "impact": "high", "recommendation": "Add more detailed content about your services, experience, and service area"})
        score -= 15
    elif word_count < 500:
        issues.append({"issue": "Content could be more detailed", "impact": "medium", "recommendation": "Expand your content to 500+ words covering services, FAQs, and local expertise"})
        score -= 8

    # Contact information
    has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text))
    has_email = bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
    if not has_phone:
        issues.append({"issue": "No phone number found on page", "impact": "medium", "recommendation": "Add your phone number visibly — AI uses this to verify you're a real business"})
        score -= 5
    if not has_email:
        issues.append({"issue": "No email address found on page", "impact": "low", "recommendation": "Include a business email address for credibility"})
        score -= 3

    return {
        "category": "Content Quality",
        "score": max(0, score),
        "issues": issues,
        "recommendations_count": len(issues)
    }


def analyze_technical(html: str, headers: dict) -> dict:
    """Analyze technical factors."""
    soup = BeautifulSoup(html, "lxml")
    issues = []
    score = 100

    # Mobile viewport
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        issues.append({"issue": "No mobile viewport meta tag", "impact": "high", "recommendation": "Add <meta name='viewport' content='width=device-width, initial-scale=1'>"})
        score -= 12

    # Open Graph tags
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    if not og_title or not og_desc:
        issues.append({"issue": "Missing Open Graph tags", "impact": "medium", "recommendation": "Add og:title and og:description meta tags for better social/AI sharing"})
        score -= 8

    # Canonical URL
    canonical = soup.find("link", rel="canonical")
    if not canonical:
        issues.append({"issue": "No canonical URL set", "impact": "medium", "recommendation": "Add a canonical link tag to prevent duplicate content issues"})
        score -= 5

    # robots.txt / sitemap hints
    robots_meta = soup.find("meta", attrs={"name": "robots"})
    if robots_meta and "noindex" in (robots_meta.get("content", "").lower()):
        issues.append({"issue": "Page set to noindex", "impact": "critical", "recommendation": "Remove the noindex directive — this blocks AI from reading your page entirely"})
        score -= 25

    # Page speed hints (check for large inline styles, excessive scripts)
    scripts = soup.find_all("script")
    if len(scripts) > 20:
        issues.append({"issue": "Excessive JavaScript files may slow page load", "impact": "low", "recommendation": "Reduce JavaScript files for faster load times — AI prefers fast sites"})
        score -= 5

    return {
        "category": "Technical Health",
        "score": max(0, score),
        "issues": issues,
        "recommendations_count": len(issues)
    }


def analyze_local_presence(html: str, business_name: str, city: str, state: str) -> dict:
    """Analyze local business presence signals."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True).lower()
    issues = []
    score = 100

    # NAP (Name, Address, Phone) consistency
    has_address = bool(re.search(r'\d+\s+[\w\s]+(?:st|street|ave|avenue|rd|road|blvd|dr|drive|ln|lane|way|ct|court)', text))
    if not has_address:
        issues.append({"issue": "No street address found", "impact": "high", "recommendation": "Add your full business address — AI needs this to recommend you for local searches"})
        score -= 15

    # Service area mentions
    state_lower = state.lower() if state else ""
    if state_lower and state_lower not in text:
        issues.append({"issue": f"State '{state}' not mentioned", "impact": "medium", "recommendation": f"Mention '{state}' in your content to strengthen local signals"})
        score -= 8

    # Google Business Profile link
    links = soup.find_all("a", href=True)
    has_gbp = any("google.com/maps" in link["href"] or "goo.gl/maps" in link["href"] for link in links)
    if not has_gbp:
        issues.append({"issue": "No Google Maps/Business Profile link", "impact": "medium", "recommendation": "Link to your Google Business Profile — this is a major trust signal for AI"})
        score -= 10

    # Social media links
    social_domains = ["facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "yelp.com"]
    found_social = sum(1 for link in links if any(domain in link["href"] for domain in social_domains))
    if found_social == 0:
        issues.append({"issue": "No social media links found", "impact": "medium", "recommendation": "Add links to your social media profiles — AI cross-references these for credibility"})
        score -= 10
    elif found_social < 3:
        issues.append({"issue": f"Only {found_social} social media link(s) found", "impact": "low", "recommendation": "Add more social media links (aim for 3+) to strengthen your online presence"})
        score -= 5

    # Reviews / testimonials
    review_keywords = ["review", "testimonial", "rating", "stars", "customer said", "feedback"]
    has_reviews = any(kw in text for kw in review_keywords)
    if not has_reviews:
        issues.append({"issue": "No reviews or testimonials on page", "impact": "high", "recommendation": "Add customer reviews/testimonials — AI heavily weights social proof"})
        score -= 12

    return {
        "category": "Local Presence",
        "score": max(0, score),
        "issues": issues,
        "recommendations_count": len(issues)
    }


async def check_ai_recommendation(business_name: str, city: str, state: str, industry: str) -> dict:
    """Check if AI recommends this business."""
    api_key = get_openai_key()
    if not api_key:
        return {
            "checked": False,
            "found": False,
            "message": "AI recommendation check skipped (API key not configured)",
            "details": []
        }

    client = AsyncOpenAI(api_key=api_key)
    queries = [
        f"Who is the best {industry} in {city}, {state}?",
        f"Recommend a {industry} near {city}, {state}",
        f"Top rated {industry} in {city} area"
    ]

    details = []
    found_count = 0

    for query in queries:
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": query}],
                max_tokens=500,
                temperature=0.3
            )
            answer = response.choices[0].message.content or ""
            mentioned = business_name.lower() in answer.lower()
            if mentioned:
                found_count += 1
            details.append({
                "query": query,
                "mentioned": mentioned,
                "response_preview": answer[:200]
            })
        except Exception as e:
            details.append({
                "query": query,
                "mentioned": False,
                "response_preview": f"Error: {str(e)}"
            })

    found = found_count > 0
    if found:
        message = f"Your business was mentioned in {found_count} of {len(queries)} AI queries!"
    else:
        message = "Your business was NOT found in any AI recommendations. This is a major opportunity."

    return {
        "checked": True,
        "found": found,
        "message": message,
        "details": details
    }


async def run_scan(scan_data: dict) -> dict:
    """Run a full AI visibility scan."""
    business_name = scan_data["business_name"]
    city = scan_data["city"]
    state = scan_data["state"]
    industry = scan_data["industry"]
    website_url = normalize_url(scan_data["website_url"])

    # Fetch the website
    page_data = await fetch_page(website_url)

    if not page_data["success"]:
        # Still run AI check even if website fetch fails
        ai_result = await check_ai_recommendation(business_name, city, state, industry)
        return {
            "business_name": business_name,
            "city": city,
            "state": state,
            "industry": industry,
            "website_url": website_url,
            "overall_score": 15,
            "grade": "F",
            "total_recommendations": 1,
            "categories": [{
                "category": "Website Accessibility",
                "score": 0,
                "issues": [{"issue": f"Could not access website: {page_data.get('error', 'Unknown error')}", "impact": "critical", "recommendation": "Make sure your website is accessible and loads properly"}],
                "recommendations_count": 1
            }],
            "ai_recommendation": ai_result
        }

    html = page_data["html"]
    headers = page_data["headers"]

    # Run all analyses
    seo = analyze_seo(html, website_url)
    content = analyze_content(html, business_name, city, industry)
    technical = analyze_technical(html, headers)
    local = analyze_local_presence(html, business_name, city, state)
    ai_result = await check_ai_recommendation(business_name, city, state, industry)

    categories = [seo, content, technical, local]
    total_recommendations = sum(c["recommendations_count"] for c in categories)

    # Calculate overall score (weighted average)
    weights = [0.25, 0.30, 0.15, 0.30]
    overall_score = round(sum(c["score"] * w for c, w in zip(categories, weights)))

    # Boost/penalty based on AI recommendation
    if ai_result.get("found"):
        overall_score = min(100, overall_score + 10)
    elif ai_result.get("checked"):
        overall_score = max(0, overall_score - 5)

    grade = grade_from_score(overall_score)

    return {
        "business_name": business_name,
        "city": city,
        "state": state,
        "industry": industry,
        "website_url": website_url,
        "overall_score": overall_score,
        "grade": grade,
        "total_recommendations": total_recommendations,
        "categories": categories,
        "ai_recommendation": ai_result
    }
