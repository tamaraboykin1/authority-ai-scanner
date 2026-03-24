"""Fulfillment system for managing client optimization tasks."""
import json
import uuid
from datetime import datetime

from app.database import get_db


async def init_fulfillment_db():
    """Create fulfillment tables."""
    db = await get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                scan_id TEXT,
                business_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                website_url TEXT,
                city TEXT,
                state TEXT,
                industry TEXT,
                initial_score INTEGER DEFAULT 0,
                current_score INTEGER DEFAULT 0,
                target_score INTEGER DEFAULT 85,
                status TEXT DEFAULT 'prospect',
                package TEXT DEFAULT '',
                monthly_rate REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS fulfillment_tasks (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                internal_steps TEXT DEFAULT '[]',
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                assigned_to TEXT DEFAULT '',
                due_date TEXT DEFAULT '',
                completed_at TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS client_activity (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        """)
        await db.commit()
    finally:
        await db.close()


# ── Client Management ──────────────────────────────────────────

async def create_client(scan_id: str, data: dict) -> str:
    """Create a client from a scan result."""
    client_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO clients (id, scan_id, business_name, email, phone, website_url,
               city, state, industry, initial_score, current_score, status, package, monthly_rate)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, scan_id, data.get("business_name", ""),
             data.get("email", ""), data.get("phone", ""),
             data.get("website_url", ""), data.get("city", ""),
             data.get("state", ""), data.get("industry", ""),
             data.get("initial_score", 0), data.get("initial_score", 0),
             "prospect", data.get("package", ""), data.get("monthly_rate", 0))
        )
        await db.commit()

        # Auto-generate fix tasks based on scan results
        if data.get("categories"):
            await _generate_tasks_from_scan(client_id, data["categories"])

        # Log activity
        await log_activity(client_id, "client_created", f"Client created from scan {scan_id}")

        return client_id
    finally:
        await db.close()


async def get_client(client_id: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}
    finally:
        await db.close()


async def get_client_by_scan(scan_id: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM clients WHERE scan_id = ?", (scan_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}
    finally:
        await db.close()


async def get_all_clients(status: str = "", limit: int = 50, offset: int = 0) -> list:
    db = await get_db()
    try:
        if status:
            cursor = await db.execute(
                "SELECT * FROM clients WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM clients ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def update_client(client_id: str, data: dict):
    db = await get_db()
    try:
        allowed = ["status", "package", "monthly_rate", "notes", "current_score", "target_score"]
        sets = []
        vals = []
        for key in allowed:
            if key in data:
                sets.append(f"{key} = ?")
                vals.append(data[key])
        if sets:
            sets.append("updated_at = ?")
            vals.append(datetime.utcnow().isoformat())
            vals.append(client_id)
            await db.execute(f"UPDATE clients SET {', '.join(sets)} WHERE id = ?", tuple(vals))
            await db.commit()
            await log_activity(client_id, "client_updated", json.dumps(data))
    finally:
        await db.close()


# ── Task Management ────────────────────────────────────────────

async def get_tasks(client_id: str, status: str = "") -> list:
    db = await get_db()
    try:
        if status:
            cursor = await db.execute(
                "SELECT * FROM fulfillment_tasks WHERE client_id = ? AND status = ? ORDER BY priority DESC, created_at ASC",
                (client_id, status)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM fulfillment_tasks WHERE client_id = ? ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, created_at ASC",
                (client_id,)
            )
        rows = await cursor.fetchall()
        tasks = []
        for row in rows:
            task = dict(row)
            if task.get("internal_steps"):
                task["internal_steps"] = json.loads(task["internal_steps"])
            tasks.append(task)
        return tasks
    finally:
        await db.close()


async def create_task(client_id: str, data: dict) -> str:
    task_id = str(uuid.uuid4())
    db = await get_db()
    try:
        steps = json.dumps(data.get("internal_steps", []))
        await db.execute(
            """INSERT INTO fulfillment_tasks (id, client_id, category, title, description,
               internal_steps, priority, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, client_id, data.get("category", ""),
             data.get("title", ""), data.get("description", ""),
             steps, data.get("priority", "medium"), "pending")
        )
        await db.commit()
        return task_id
    finally:
        await db.close()


async def update_task(task_id: str, data: dict):
    db = await get_db()
    try:
        allowed = ["status", "notes", "assigned_to", "due_date", "internal_steps"]
        sets = []
        vals = []
        for key in allowed:
            if key in data:
                val = data[key]
                if key == "internal_steps" and isinstance(val, list):
                    val = json.dumps(val)
                sets.append(f"{key} = ?")
                vals.append(val)
        if data.get("status") == "completed":
            sets.append("completed_at = ?")
            vals.append(datetime.utcnow().isoformat())
        if sets:
            vals.append(task_id)
            await db.execute(f"UPDATE fulfillment_tasks SET {', '.join(sets)} WHERE id = ?", tuple(vals))
            await db.commit()
    finally:
        await db.close()


async def delete_task(task_id: str):
    db = await get_db()
    try:
        await db.execute("DELETE FROM fulfillment_tasks WHERE id = ?", (task_id,))
        await db.commit()
    finally:
        await db.close()


# ── Activity Log ───────────────────────────────────────────────

async def log_activity(client_id: str, action: str, details: str = ""):
    db = await get_db()
    try:
        activity_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO client_activity (id, client_id, action, details) VALUES (?, ?, ?, ?)",
            (activity_id, client_id, action, details)
        )
        await db.commit()
    finally:
        await db.close()


async def get_activity(client_id: str, limit: int = 20) -> list:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM client_activity WHERE client_id = ? ORDER BY created_at DESC LIMIT ?",
            (client_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


# ── Fulfillment Stats ─────────────────────────────────────────

async def get_fulfillment_stats() -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) as total FROM clients")
        total_clients = dict(await cursor.fetchone())["total"]

        cursor = await db.execute("SELECT COUNT(*) as c FROM clients WHERE status = 'active'")
        active_clients = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT COUNT(*) as c FROM clients WHERE status = 'prospect'")
        prospects = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT COUNT(*) as c FROM fulfillment_tasks WHERE status = 'pending'")
        pending_tasks = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT COUNT(*) as c FROM fulfillment_tasks WHERE status = 'in_progress'")
        in_progress_tasks = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT COUNT(*) as c FROM fulfillment_tasks WHERE status = 'completed'")
        completed_tasks = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT SUM(monthly_rate) as revenue FROM clients WHERE status = 'active'")
        row = await cursor.fetchone()
        monthly_revenue = dict(row)["revenue"] or 0

        cursor = await db.execute(
            "SELECT AVG(current_score - initial_score) as avg_improvement FROM clients WHERE current_score > initial_score"
        )
        row = await cursor.fetchone()
        avg_improvement = round(dict(row)["avg_improvement"] or 0, 1)

        return {
            "total_clients": total_clients,
            "active_clients": active_clients,
            "prospects": prospects,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completed_tasks": completed_tasks,
            "monthly_revenue": monthly_revenue,
            "avg_score_improvement": avg_improvement
        }
    finally:
        await db.close()


# ── Auto-generate Tasks from Scan ─────────────────────────────

TASK_TEMPLATES = {
    "Website SEO": {
        "Missing page title": {
            "title": "Fix Page Title Tag",
            "priority": "high",
            "steps": [
                "Open client's website CMS/WordPress admin",
                "Navigate to homepage settings",
                "Add descriptive title: '[Business Name] - [Primary Service] in [City]'",
                "Save and verify title shows in browser tab",
                "Check with site:domain.com in Google"
            ]
        },
        "Page title too short": {
            "title": "Optimize Page Title",
            "priority": "medium",
            "steps": [
                "Review current title in CMS",
                "Expand to include: business name + primary service + city",
                "Keep under 60 characters",
                "Save and verify"
            ]
        },
        "Missing meta description": {
            "title": "Add Meta Description",
            "priority": "high",
            "steps": [
                "Open CMS/WordPress admin → SEO settings or Yoast/RankMath",
                "Write 150-160 character description including business name, service, city",
                "Include a call to action",
                "Save and verify in page source"
            ]
        },
        "Missing H1 heading": {
            "title": "Add H1 Heading",
            "priority": "high",
            "steps": [
                "Edit homepage content",
                "Add clear H1 with business name and primary service",
                "Ensure only one H1 per page",
                "Save and verify in page inspector"
            ]
        },
        "No structured data (Schema.org)": {
            "title": "Add Schema.org Structured Data",
            "priority": "critical",
            "steps": [
                "Create LocalBusiness JSON-LD schema",
                "Include: name, address, phone, hours, services, geo coordinates",
                "Add to homepage <head> section",
                "Validate with Google Rich Results Test",
                "Test with Schema.org validator"
            ]
        },
        "No LocalBusiness schema": {
            "title": "Add LocalBusiness Schema",
            "priority": "high",
            "steps": [
                "Create LocalBusiness JSON-LD with all NAP data",
                "Add opening hours, service area, price range",
                "Inject into page head",
                "Validate with Google's testing tool"
            ]
        },
        "images missing alt text": {
            "title": "Add Alt Text to Images",
            "priority": "medium",
            "steps": [
                "Audit all images on the site",
                "Add descriptive alt text to each image",
                "Include relevant keywords naturally",
                "Save and verify"
            ]
        },
        "Website not using HTTPS": {
            "title": "Enable HTTPS/SSL",
            "priority": "critical",
            "steps": [
                "Check hosting provider for free SSL (Let's Encrypt)",
                "Enable SSL certificate",
                "Set up HTTP → HTTPS redirect",
                "Update all internal links to https://",
                "Verify no mixed content warnings"
            ]
        }
    },
    "Content Quality": {
        "Business name not found": {
            "title": "Add Business Name to Content",
            "priority": "high",
            "steps": [
                "Add business name to homepage header/hero section",
                "Include in About section",
                "Add to footer",
                "Mention naturally in service descriptions"
            ]
        },
        "City": {
            "title": "Add City/Location Keywords",
            "priority": "high",
            "steps": [
                "Add city name to page title and H1",
                "Create 'Service Area' section mentioning city and nearby areas",
                "Include city in meta description",
                "Add city to image alt tags where relevant"
            ]
        },
        "Industry": {
            "title": "Add Industry Keywords",
            "priority": "medium",
            "steps": [
                "Review main service/industry terms",
                "Add industry keywords to title, H1, and headings",
                "Create detailed service descriptions using industry terms",
                "Add FAQ section with industry-specific questions"
            ]
        },
        "thin content": {
            "title": "Expand Page Content",
            "priority": "high",
            "steps": [
                "Write detailed About section (200+ words)",
                "Add comprehensive service descriptions",
                "Create FAQ section (8-10 questions)",
                "Add service area/coverage content",
                "Target 1000+ total words on homepage"
            ]
        },
        "No phone number": {
            "title": "Add Phone Number to Page",
            "priority": "medium",
            "steps": [
                "Add phone number to header/navigation",
                "Include in footer",
                "Add click-to-call link for mobile"
            ]
        },
        "No email address": {
            "title": "Add Email to Page",
            "priority": "low",
            "steps": [
                "Add business email to contact section",
                "Include in footer",
                "Consider contact form as alternative"
            ]
        }
    },
    "Technical Health": {
        "No mobile viewport": {
            "title": "Add Mobile Viewport Meta Tag",
            "priority": "high",
            "steps": [
                "Add <meta name='viewport' content='width=device-width, initial-scale=1'> to <head>",
                "Test mobile responsiveness",
                "Fix any layout issues on mobile"
            ]
        },
        "Missing Open Graph": {
            "title": "Add Open Graph Tags",
            "priority": "medium",
            "steps": [
                "Add og:title, og:description, og:image, og:url meta tags",
                "Add og:type='website' or 'business.business'",
                "Test with Facebook Sharing Debugger",
                "Verify image displays correctly when shared"
            ]
        },
        "No canonical URL": {
            "title": "Add Canonical URL",
            "priority": "medium",
            "steps": [
                "Add <link rel='canonical' href='full-page-url'> to <head>",
                "Ensure canonical points to preferred URL version",
                "Verify in page source"
            ]
        },
        "noindex": {
            "title": "Remove Noindex Directive (CRITICAL)",
            "priority": "critical",
            "steps": [
                "URGENT: Remove noindex from robots meta tag",
                "Check for noindex in robots.txt",
                "Verify page is indexable",
                "Submit to Google Search Console for re-indexing"
            ]
        }
    },
    "Local Presence": {
        "No street address": {
            "title": "Add Business Address",
            "priority": "high",
            "steps": [
                "Add full street address to footer",
                "Include in Contact page",
                "Add to LocalBusiness schema",
                "Embed Google Map on contact page"
            ]
        },
        "State": {
            "title": "Add State/Region References",
            "priority": "medium",
            "steps": [
                "Add state name to service area section",
                "Include in meta description",
                "Add to footer address"
            ]
        },
        "No Google Maps": {
            "title": "Add Google Business Profile Link",
            "priority": "high",
            "steps": [
                "Verify Google Business Profile is claimed and complete",
                "Add Google Maps embed to contact page",
                "Link to Google Business Profile",
                "Ensure NAP matches exactly"
            ]
        },
        "No social media": {
            "title": "Add Social Media Links",
            "priority": "medium",
            "steps": [
                "Create/claim Facebook, Instagram, LinkedIn profiles",
                "Add social links to website footer",
                "Ensure business info matches across all profiles",
                "Add social media schema markup"
            ]
        },
        "No reviews": {
            "title": "Add Reviews/Testimonials",
            "priority": "high",
            "steps": [
                "Collect customer testimonials",
                "Add testimonials section to homepage",
                "Add Review schema markup",
                "Link to Google Reviews",
                "Implement a review request system"
            ]
        }
    }
}


async def _generate_tasks_from_scan(client_id: str, categories: list):
    """Auto-generate fix tasks based on scan issues."""
    db = await get_db()
    try:
        for category in categories:
            cat_name = category.get("category", "")
            templates = TASK_TEMPLATES.get(cat_name, {})

            for issue in category.get("issues", []):
                issue_text = issue.get("issue", "")
                # Find matching template
                matched = False
                for key, template in templates.items():
                    if key.lower() in issue_text.lower():
                        task_id = str(uuid.uuid4())
                        await db.execute(
                            """INSERT INTO fulfillment_tasks (id, client_id, category, title,
                               description, internal_steps, priority, status)
                               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                            (task_id, client_id, cat_name, template["title"],
                             issue_text, json.dumps(template["steps"]),
                             template["priority"])
                        )
                        matched = True
                        break

                if not matched:
                    # Create generic task for unmatched issues
                    task_id = str(uuid.uuid4())
                    await db.execute(
                        """INSERT INTO fulfillment_tasks (id, client_id, category, title,
                           description, internal_steps, priority, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                        (task_id, client_id, cat_name, f"Fix: {issue_text[:80]}",
                         issue_text, json.dumps(["Investigate and resolve this issue",
                                                  "Verify fix is working"]),
                         issue.get("impact", "medium"))
                    )

        await db.commit()
    finally:
        await db.close()
