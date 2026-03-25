"""Social media content generation and auto-posting agent."""
import os
import json
import uuid
import logging
import aiosqlite
import httpx
from datetime import datetime, timedelta
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")

# Meta API config
META_PAGE_ACCESS_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN", "")
META_PAGE_ID = os.environ.get("META_PAGE_ID", "")
META_IG_USER_ID = os.environ.get("META_IG_USER_ID", "")

# Content themes for AI visibility / authority AI niche
CONTENT_THEMES = [
    {
        "theme": "ai_visibility_tips",
        "description": "Tips on how businesses can become more visible to AI assistants like ChatGPT, Google AI, Claude",
        "hashtags": ["#AIVisibility", "#ChatGPT", "#BusinessGrowth", "#AIMarketing", "#DigitalMarketing"]
    },
    {
        "theme": "ai_stats_facts",
        "description": "Shocking stats about AI search adoption and how it's changing customer behavior",
        "hashtags": ["#AISearch", "#FutureOfSearch", "#BusinessTips", "#AIRevolution", "#Marketing2024"]
    },
    {
        "theme": "client_results",
        "description": "Case study style posts about businesses that improved their AI visibility scores",
        "hashtags": ["#ClientResults", "#CaseStudy", "#AIOptimization", "#BusinessSuccess", "#ROI"]
    },
    {
        "theme": "industry_insights",
        "description": "How specific industries (restaurants, lawyers, dentists, etc.) are being affected by AI search",
        "hashtags": ["#IndustryInsights", "#LocalBusiness", "#SmallBusiness", "#AITrends", "#LocalSEO"]
    },
    {
        "theme": "urgency_fomo",
        "description": "Why businesses that don't optimize for AI NOW will fall behind competitors",
        "hashtags": ["#DontGetLeftBehind", "#AIOptimization", "#CompetitiveEdge", "#BusinessStrategy", "#ActNow"]
    },
    {
        "theme": "how_ai_works",
        "description": "Educational content explaining how AI assistants choose which businesses to recommend",
        "hashtags": ["#HowAIWorks", "#AIEducation", "#BusinessOwners", "#TechTips", "#AIRecommendations"]
    },
    {
        "theme": "free_scan_cta",
        "description": "Direct call-to-action posts encouraging people to get their free AI visibility scan",
        "hashtags": ["#FreeScan", "#AIVisibilityScan", "#FreeAudit", "#BusinessTools", "#GetFound"]
    },
    {
        "theme": "authority_brand",
        "description": "Brand-building posts establishing Authority AI Systems as the go-to experts",
        "hashtags": ["#AuthorityAI", "#AIExperts", "#TrustedPartner", "#BusinessGrowth", "#AIAgency"]
    },
]

# Posting schedule: times throughout the day (UTC)
DEFAULT_POSTING_TIMES = [
    "09:00",  # Morning
    "12:00",  # Lunch
    "15:00",  # Afternoon
    "18:00",  # Evening
    "21:00",  # Night
]


async def init_social_media_db():
    """Initialize social media tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS social_posts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                caption TEXT NOT NULL,
                hashtags TEXT DEFAULT '',
                media_url TEXT DEFAULT '',
                theme TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                scheduled_at TEXT DEFAULT '',
                posted_at TEXT DEFAULT '',
                post_id TEXT DEFAULT '',
                post_url TEXT DEFAULT '',
                error TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS social_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.commit()


async def generate_social_content(theme: str = "", platform: str = "facebook", count: int = 1) -> list:
    """Generate social media content using GPT-4o-mini."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return [{"error": "OpenAI API key not configured"}]

    client = AsyncOpenAI(api_key=api_key)

    # Pick a theme if not specified
    if not theme:
        import random
        theme_obj = random.choice(CONTENT_THEMES)
    else:
        theme_obj = next((t for t in CONTENT_THEMES if t["theme"] == theme), CONTENT_THEMES[0])

    platform_guidelines = {
        "facebook": "Facebook post. Can be longer (1-3 paragraphs). Use emojis sparingly. Include a clear CTA. Max 500 words.",
        "instagram": "Instagram caption. Hook in first line. Use line breaks for readability. 5-10 relevant hashtags at the end. Max 300 words.",
        "tiktok": "TikTok caption. Very short and punchy. Use trending language. 3-5 hashtags. Max 150 characters for the main caption.",
    }

    scanner_url = os.environ.get("SCANNER_URL", "https://authority-ai-scanner-1.onrender.com")

    system_prompt = f"""You are an ELECTRIFYING social media content creator for Authority AI Systems. You write like Gary Vee meets Grant Cardone — HIGH ENERGY, bold, punchy, and impossible to scroll past.

You help businesses become visible to AI assistants like ChatGPT, Google AI, Claude, and Perplexity.

Target audience: Small to medium business owners (restaurants, lawyers, dentists, contractors, real estate agents, etc.)
Scanner URL: {scanner_url}

Generate {count} unique {platform_guidelines.get(platform, platform_guidelines['facebook'])}

Theme: {theme_obj['description']}

STYLE RULES (CRITICAL):
- Start EVERY post with a pattern-interrupt hook that STOPS the scroll. Examples:
  "Your competitor just stole 50 customers from you. Here's how..."
  "I asked ChatGPT to find the best dentist in Dallas. YOUR business wasn't on the list."
  "STOP scrolling. If you own a business, this will change everything."
  "93% of business owners don't know this exists yet..."
- Write like you're talking to a friend, NOT a corporate newsletter
- Use SHORT punchy sentences. One idea per line. Break it up.
- Use strategic emojis to add energy (fire, lightning, pointing, sirens, etc.)
- Create URGENCY — make them feel like they're losing money every day they wait
- Include real-world scenarios (e.g. "Someone just asked Siri for the best plumber near them. Did YOUR business show up?")
- End with a STRONG call-to-action — get the free scan, DM us, link in bio
- Sound like a real person who is genuinely fired up about helping businesses WIN
- NEVER sound corporate, boring, or generic
- NEVER use words like "revolutionize", "game-changer", "leverage", "synergy", "landscape"
- Keep it EXCITING — every post should make the reader feel like they NEED to act NOW
- Use the scanner URL when directing people to get their free scan

Return as JSON array: [{{"caption": "...", "hashtags": "..."}}]
Only return the JSON, no other text."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate {count} {platform} post(s) about: {theme_obj['description']}"}
            ],
            temperature=0.9,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()
        # Parse JSON from response
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        posts = json.loads(content)
        
        # Add theme info
        for post in posts:
            post["theme"] = theme_obj["theme"]
            post["platform"] = platform
            if not post.get("hashtags"):
                post["hashtags"] = " ".join(theme_obj["hashtags"])

        return posts

    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return [{"error": str(e)}]


async def save_social_post(post_data: dict) -> str:
    """Save a social media post to the database."""
    post_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO social_posts (id, platform, content_type, caption, hashtags, media_url, theme, status, scheduled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_id,
            post_data.get("platform", "facebook"),
            post_data.get("content_type", "text"),
            post_data.get("caption", ""),
            post_data.get("hashtags", ""),
            post_data.get("media_url", ""),
            post_data.get("theme", ""),
            post_data.get("status", "draft"),
            post_data.get("scheduled_at", ""),
        ))
        await db.commit()
    return post_id


async def get_social_posts(status: str = "", platform: str = "", limit: int = 50) -> list:
    """Get social media posts."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM social_posts WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_social_post(post_id: str) -> dict:
    """Get a single social media post."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_social_post(post_id: str, updates: dict):
    """Update a social media post."""
    allowed_fields = ["caption", "hashtags", "media_url", "status", "scheduled_at", "posted_at", "post_id", "post_url", "error"]
    set_parts = []
    params = []
    for field in allowed_fields:
        if field in updates:
            set_parts.append(f"{field} = ?")
            params.append(updates[field])
    
    if not set_parts:
        return
    
    params.append(post_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE social_posts SET {', '.join(set_parts)} WHERE id = ?", params)
        await db.commit()


async def delete_social_post(post_id: str):
    """Delete a social media post."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM social_posts WHERE id = ?", (post_id,))
        await db.commit()


async def post_to_facebook(caption: str, media_url: str = "") -> dict:
    """Post content to Facebook Page using Graph API."""
    if not META_PAGE_ACCESS_TOKEN or not META_PAGE_ID:
        return {"success": False, "error": "Meta Page access token or Page ID not configured"}

    try:
        async with httpx.AsyncClient() as client:
            if media_url:
                # Photo post
                response = await client.post(
                    f"https://graph.facebook.com/v19.0/{META_PAGE_ID}/photos",
                    data={
                        "url": media_url,
                        "message": caption,
                        "access_token": META_PAGE_ACCESS_TOKEN,
                    }
                )
            else:
                # Text post
                response = await client.post(
                    f"https://graph.facebook.com/v19.0/{META_PAGE_ID}/feed",
                    data={
                        "message": caption,
                        "access_token": META_PAGE_ACCESS_TOKEN,
                    }
                )

            result = response.json()
            if "id" in result:
                return {"success": True, "post_id": result["id"], "error": ""}
            else:
                error = result.get("error", {}).get("message", str(result))
                return {"success": False, "error": error}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def post_to_instagram(caption: str, media_url: str) -> dict:
    """Post content to Instagram using Graph API (requires media_url)."""
    if not META_PAGE_ACCESS_TOKEN or not META_IG_USER_ID:
        return {"success": False, "error": "Meta IG user ID or access token not configured"}

    if not media_url:
        return {"success": False, "error": "Instagram requires an image or video URL"}

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Create media container
            create_response = await client.post(
                f"https://graph.facebook.com/v19.0/{META_IG_USER_ID}/media",
                data={
                    "image_url": media_url,
                    "caption": caption,
                    "access_token": META_PAGE_ACCESS_TOKEN,
                }
            )
            create_result = create_response.json()

            if "id" not in create_result:
                error = create_result.get("error", {}).get("message", str(create_result))
                return {"success": False, "error": f"Failed to create media container: {error}"}

            container_id = create_result["id"]

            # Step 2: Publish the container
            publish_response = await client.post(
                f"https://graph.facebook.com/v19.0/{META_IG_USER_ID}/media_publish",
                data={
                    "creation_id": container_id,
                    "access_token": META_PAGE_ACCESS_TOKEN,
                }
            )
            publish_result = publish_response.json()

            if "id" in publish_result:
                return {"success": True, "post_id": publish_result["id"], "error": ""}
            else:
                error = publish_result.get("error", {}).get("message", str(publish_result))
                return {"success": False, "error": f"Failed to publish: {error}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def publish_post(post_id: str) -> dict:
    """Publish a scheduled/draft post to its platform."""
    post = await get_social_post(post_id)
    if not post:
        return {"success": False, "error": "Post not found"}

    caption = post["caption"]
    if post["hashtags"]:
        caption += "\n\n" + post["hashtags"]

    platform = post["platform"]
    media_url = post.get("media_url", "")

    if platform == "facebook":
        result = await post_to_facebook(caption, media_url)
    elif platform == "instagram":
        result = await post_to_instagram(caption, media_url)
    else:
        result = {"success": False, "error": f"Platform '{platform}' not yet supported for auto-posting"}

    if result["success"]:
        await update_social_post(post_id, {
            "status": "posted",
            "posted_at": datetime.utcnow().isoformat(),
            "post_id": result.get("post_id", ""),
        })
    else:
        await update_social_post(post_id, {
            "status": "failed",
            "error": result.get("error", "Unknown error"),
        })

    return result


async def generate_and_schedule_content(days: int = 7):
    """Generate and schedule content for the next N days across platforms."""
    platforms = ["facebook"]
    if META_IG_USER_ID:
        platforms.append("instagram")

    posts_created = 0
    now = datetime.utcnow()

    for day_offset in range(days):
        target_date = now + timedelta(days=day_offset)

        for time_str in DEFAULT_POSTING_TIMES:
            hour, minute = map(int, time_str.split(":"))
            scheduled_dt = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Skip past times
            if scheduled_dt <= now:
                continue

            # Rotate through themes
            theme_idx = (day_offset * len(DEFAULT_POSTING_TIMES) + DEFAULT_POSTING_TIMES.index(time_str)) % len(CONTENT_THEMES)
            theme = CONTENT_THEMES[theme_idx]["theme"]

            for platform in platforms:
                content = await generate_social_content(theme=theme, platform=platform, count=1)
                if content and not content[0].get("error"):
                    post_data = content[0]
                    post_data["platform"] = platform
                    post_data["status"] = "scheduled"
                    post_data["scheduled_at"] = scheduled_dt.isoformat()
                    await save_social_post(post_data)
                    posts_created += 1

    return {"posts_created": posts_created, "days": days, "platforms": platforms}


async def auto_generate_daily_content():
    """Auto-generate content for the next 24 hours if not enough posts are scheduled."""
    import random

    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")

    # Check how many posts are already scheduled for today
    all_scheduled = await get_social_posts(status="scheduled", limit=200)
    today_scheduled = [p for p in all_scheduled if p.get("scheduled_at", "").startswith(today_str)]

    # Also check tomorrow
    tomorrow = now + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    tomorrow_scheduled = [p for p in all_scheduled if p.get("scheduled_at", "").startswith(tomorrow_str)]

    platforms = ["facebook"]
    if META_IG_USER_ID:
        platforms.append("instagram")

    posts_created = 0

    # Generate for today if we have fewer than 5 posts scheduled
    for target_date, target_str, existing in [(now, today_str, today_scheduled), (tomorrow, tomorrow_str, tomorrow_scheduled)]:
        existing_count = len(existing)
        if existing_count >= len(DEFAULT_POSTING_TIMES) * len(platforms):
            logger.debug(f"Already have {existing_count} posts scheduled for {target_str}, skipping generation")
            continue

        logger.info(f"Generating content for {target_str} ({existing_count} existing, need {len(DEFAULT_POSTING_TIMES) * len(platforms)})")

        for time_str in DEFAULT_POSTING_TIMES:
            hour, minute = map(int, time_str.split(":"))
            scheduled_dt = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Skip times that have already passed
            if scheduled_dt <= now:
                continue

            # Check if we already have a post at this time
            time_prefix = scheduled_dt.isoformat()[:16]  # Match up to minutes
            already_exists = any(p.get("scheduled_at", "").startswith(time_prefix) for p in existing)
            if already_exists:
                continue

            # Pick a random theme for variety
            theme_obj = random.choice(CONTENT_THEMES)

            for platform in platforms:
                try:
                    content = await generate_social_content(theme=theme_obj["theme"], platform=platform, count=1)
                    if content and not content[0].get("error"):
                        post_data = content[0]
                        post_data["platform"] = platform
                        post_data["status"] = "scheduled"
                        post_data["scheduled_at"] = scheduled_dt.isoformat()
                        await save_social_post(post_data)
                        posts_created += 1
                        logger.info(f"Scheduled {platform} post for {scheduled_dt.isoformat()} - theme: {theme_obj['theme']}")
                except Exception as e:
                    logger.error(f"Error generating {platform} content for {scheduled_dt}: {e}")

                # Small delay between API calls to avoid rate limits
                await asyncio.sleep(2)

    if posts_created > 0:
        logger.info(f"Auto-generated {posts_created} new posts")
    return posts_created


async def process_scheduled_posts():
    """Background task: auto-generate content daily and publish posts on schedule."""
    # Wait 30 seconds on startup for DB init
    await asyncio.sleep(30)
    logger.info("Social media scheduler started - will generate and post content automatically")

    last_generation_date = ""

    while True:
        try:
            now = datetime.utcnow()
            today_str = now.strftime("%Y-%m-%d")

            # Auto-generate content once per day (or on startup if none exists)
            if today_str != last_generation_date:
                logger.info(f"Running daily content generation for {today_str}")
                try:
                    created = await auto_generate_daily_content()
                    last_generation_date = today_str
                    if created > 0:
                        logger.info(f"Daily generation complete: {created} new posts created")
                except Exception as gen_err:
                    logger.error(f"Error in daily content generation: {gen_err}")

            # Publish posts that are due
            posts = await get_social_posts(status="scheduled")
            published = 0

            for post in posts:
                scheduled_at = post.get("scheduled_at", "")
                if not scheduled_at:
                    continue

                try:
                    scheduled_time = datetime.fromisoformat(scheduled_at)
                    if now >= scheduled_time:
                        result = await publish_post(post["id"])
                        if result.get("success"):
                            published += 1
                            logger.info(f"Published post {post['id']} to {post['platform']}")
                        else:
                            logger.error(f"Failed to publish post {post['id']}: {result.get('error')}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid scheduled_at for post {post['id']}: {e}")

            if published > 0:
                logger.info(f"Published {published} scheduled posts")

        except Exception as e:
            logger.error(f"Error in social media scheduler: {e}")

        # Check every 5 minutes
        await asyncio.sleep(300)


async def get_social_stats() -> dict:
    """Get social media posting stats."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM social_posts WHERE status = 'posted'")
        posted = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM social_posts WHERE status = 'scheduled'")
        scheduled = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM social_posts WHERE status = 'draft'")
        drafts = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM social_posts WHERE status = 'failed'")
        failed = (await cursor.fetchone())[0]

        return {
            "posted": posted,
            "scheduled": scheduled,
            "drafts": drafts,
            "failed": failed,
            "total": posted + scheduled + drafts + failed,
            "meta_configured": bool(META_PAGE_ACCESS_TOKEN and META_PAGE_ID),
            "instagram_configured": bool(META_IG_USER_ID),
        }


# Need asyncio import for sleep
import asyncio
