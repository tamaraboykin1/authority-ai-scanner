import base64
import csv
import io
import json
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import (
    init_db, save_scan, update_scan_results, update_scan_error,
    get_scan, get_scan_by_email, get_all_leads, get_stats
)
from app.scanner import run_scan
from app.chatbot import get_chat_response
from app.leads import (
    init_leads_db, save_chatbot_lead, get_chatbot_leads, get_chatbot_lead,
    update_lead_status, save_message, get_conversation, get_all_conversations,
    create_follow_up, get_follow_ups, mark_follow_up_sent,
    save_prospect, get_prospects, update_prospect_status,
    get_dashboard_stats, get_setting, set_setting
)
from app.follow_ups import (
    get_follow_up_sequence, get_outreach_template, render_template,
    OUTREACH_TEMPLATES
)
from app.outreach import analyze_website_quality, scan_prospect_websites
from app.fulfillment import (
    init_fulfillment_db, create_client, get_client, get_client_by_scan,
    get_all_clients, update_client, get_tasks, create_task, update_task,
    delete_task, log_activity, get_activity, get_fulfillment_stats
)
from app.affiliates import (
    init_affiliates_db, apply_as_affiliate, get_affiliate, get_affiliate_by_code,
    get_affiliate_by_email, affiliate_login, get_all_affiliates,
    approve_affiliate, reject_affiliate, update_affiliate,
    track_referral, convert_referral, get_affiliate_referrals,
    get_referral_by_scan, record_payout, get_affiliate_payouts,
    get_affiliate_stats
)
from app.report import generate_report_html

load_dotenv()

ADMIN_KEY = os.environ.get("ADMIN_KEY", "a7x9k2m4")
AUTH_USER = os.environ.get("AUTH_USER", "")
AUTH_PASS = os.environ.get("AUTH_PASS", "")
NOTIFICATION_EMAIL = os.environ.get("NOTIFICATION_EMAIL", "")


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not AUTH_USER or not AUTH_PASS:
            return await call_next(request)
        # Allow CORS preflight requests through
        if request.method == "OPTIONS":
            return await call_next(request)
        # Allow public endpoints without auth
        public_paths = ("/healthz", "/", "/index.html")
        public_prefixes = ("/api/chat", "/api/scan", "/api/affiliate", "/assets/", "/static/", "/chatbot-widget.js", "/report/")
        if request.url.path in public_paths or any(request.url.path.startswith(p) for p in public_prefixes):
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                user, password = decoded.split(":", 1)
                if secrets.compare_digest(user, AUTH_USER) and secrets.compare_digest(password, AUTH_PASS):
                    return await call_next(request)
            except Exception:
                pass
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Scanner"'},
            content="Unauthorized"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_leads_db()
    await init_fulfillment_db()
    await init_affiliates_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if AUTH_USER and AUTH_PASS:
    app.add_middleware(BasicAuthMiddleware)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════
# SCANNER ENDPOINTS (existing)
# ═══════════════════════════════════════════════════════════════

async def process_scan(scan_id: str, scan_data: dict):
    try:
        results = await run_scan(scan_data)
        await update_scan_results(scan_id, results)
    except Exception as e:
        await update_scan_error(scan_id, str(e))


@app.post("/api/scan")
async def start_scan(data: dict, background_tasks: BackgroundTasks):
    # Normalize field names (frontend may send 'website' instead of 'website_url')
    if "website" in data and "website_url" not in data:
        data["website_url"] = data.pop("website")

    existing = await get_scan_by_email(data.get("email", ""))
    if existing and existing.get("results"):
        results = json.loads(existing["results"])
        return {
            "scan_id": existing["id"],
            "status": "already_scanned",
            "results": results
        }

    scan_id = str(uuid.uuid4())
    await save_scan(scan_id, data)
    background_tasks.add_task(process_scan, scan_id, data)
    return {"scan_id": scan_id, "status": "processing"}


@app.get("/api/scan/{scan_id}")
async def get_scan_results(scan_id: str):
    scan = await get_scan(scan_id)
    if not scan:
        return {"error": "Scan not found", "status": "not_found"}

    if scan["status"] == "processing":
        return {"scan_id": scan_id, "status": "processing"}

    if scan["status"] == "error":
        error_data = json.loads(scan["results"]) if scan["results"] else {}
        return {"scan_id": scan_id, "status": "error", "error": error_data.get("error", "Unknown error")}

    results = json.loads(scan["results"]) if scan["results"] else {}
    return {
        "scan_id": scan_id,
        "status": "complete",
        "results": results
    }


# ═══════════════════════════════════════════════════════════════
# CHATBOT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post("/api/chat")
async def chat(data: dict):
    """Handle chatbot conversation."""
    session_id = data.get("session_id", str(uuid.uuid4()))
    user_message = data.get("message", "").strip()

    if not user_message:
        return {"error": "Message is required"}

    # Save user message
    await save_message(session_id, "user", user_message)

    # Get conversation history
    history = await get_conversation(session_id)
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Get AI response
    result = await get_chat_response(messages)

    # Save assistant response
    await save_message(session_id, "assistant", result["response"])

    # If lead data was extracted, save it
    lead_saved = False
    lead_id = None
    if result.get("lead_data"):
        lead_data = result["lead_data"]
        lead_data["source"] = "chatbot"
        lead_id = await save_chatbot_lead(lead_data)
        lead_saved = True

        # Create follow-up sequence for this lead
        sequence = get_follow_up_sequence("chatbot_lead")
        for step_template in sequence:
            variables = {**lead_data, "scanner_url": os.environ.get("SCANNER_URL", "")}
            subject = render_template(step_template["subject"], variables)
            body = render_template(step_template["body"], variables)
            await create_follow_up(
                lead_id=lead_id,
                lead_type="chatbot",
                step=step_template["step"],
                subject=subject,
                body=body
            )

    return {
        "session_id": session_id,
        "response": result["response"],
        "lead_saved": lead_saved,
        "lead_id": lead_id
    }


@app.post("/api/chat/lead")
async def save_lead_directly(data: dict):
    """Save a lead directly (from form submission)."""
    lead_id = await save_chatbot_lead(data)

    # Create follow-up sequence
    sequence = get_follow_up_sequence("chatbot_lead")
    for step_template in sequence:
        variables = {**data, "scanner_url": os.environ.get("SCANNER_URL", "")}
        subject = render_template(step_template["subject"], variables)
        body = render_template(step_template["body"], variables)
        await create_follow_up(
            lead_id=lead_id,
            lead_type="chatbot",
            step=step_template["step"],
            subject=subject,
            body=body
        )

    return {"lead_id": lead_id, "status": "saved"}


@app.get("/api/chat/widget.js")
async def chatbot_widget():
    """Serve the chatbot widget JavaScript."""
    widget_path = Path(__file__).parent.parent / "static" / "chatbot-widget.js"
    if widget_path.exists():
        return FileResponse(str(widget_path), media_type="application/javascript")
    return Response(content="// Widget not found", media_type="application/javascript")


# ═══════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS (enhanced)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/admin/stats")
async def admin_stats(admin_key: str = Query(default="")):
    stats = await get_stats()
    return stats


@app.get("/api/admin/dashboard")
async def admin_dashboard(admin_key: str = Query(default="")):
    """Combined dashboard with all stats."""
    return await get_dashboard_stats()


@app.get("/api/admin/leads")
async def admin_leads(
    admin_key: str = Query(default=""),
    limit: int = Query(default=50),
    offset: int = Query(default=0)
):
    leads = await get_all_leads(limit, offset)
    result = []
    for lead in leads:
        results_data = json.loads(lead["results"]) if lead.get("results") else {}
        result.append({
            "id": lead["id"],
            "business_name": lead["business_name"],
            "city": lead["city"],
            "state": lead["state"],
            "industry": lead["industry"],
            "website_url": lead["website_url"],
            "email": lead["email"],
            "phone": lead.get("phone", ""),
            "score": results_data.get("overall_score", 0),
            "grade": results_data.get("grade", "N/A"),
            "created_at": lead["created_at"]
        })
    return {"leads": result, "total": len(result)}


@app.get("/api/admin/chatbot-leads")
async def admin_chatbot_leads(
    admin_key: str = Query(default=""),
    limit: int = Query(default=50),
    offset: int = Query(default=0)
):
    """Get leads from chatbot conversations."""
    leads = await get_chatbot_leads(limit, offset)
    return {"leads": leads, "total": len(leads)}


@app.post("/api/admin/chatbot-leads/{lead_id}/status")
async def admin_update_lead_status(lead_id: str, data: dict, admin_key: str = Query(default="")):
    """Update a chatbot lead's status."""
    await update_lead_status(lead_id, data.get("status", "new"), data.get("notes", ""))
    return {"status": "updated"}


@app.get("/api/admin/conversations")
async def admin_conversations(admin_key: str = Query(default=""), limit: int = Query(default=50)):
    """Get all chatbot conversation sessions."""
    conversations = await get_all_conversations(limit)
    return {"conversations": conversations}


@app.get("/api/admin/conversations/{session_id}")
async def admin_conversation_detail(session_id: str, admin_key: str = Query(default="")):
    """Get full conversation history for a session."""
    messages = await get_conversation(session_id)
    return {"session_id": session_id, "messages": messages}


@app.get("/api/admin/follow-ups")
async def admin_follow_ups(
    admin_key: str = Query(default=""),
    lead_id: str = Query(default=""),
    status: str = Query(default="")
):
    """Get follow-up emails."""
    follow_ups = await get_follow_ups(lead_id, status)
    return {"follow_ups": follow_ups}


@app.post("/api/admin/follow-ups/{fu_id}/sent")
async def admin_mark_follow_up_sent(fu_id: str, admin_key: str = Query(default="")):
    """Mark a follow-up as sent."""
    await mark_follow_up_sent(fu_id)
    return {"status": "marked_sent"}


@app.get("/api/admin/export")
async def admin_export(admin_key: str = Query(default="")):
    leads = await get_all_leads(limit=10000, offset=0)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Business Name", "City", "State", "Industry", "Website", "Email", "Phone", "Score", "Grade", "Date"])

    for lead in leads:
        results_data = json.loads(lead["results"]) if lead.get("results") else {}
        writer.writerow([
            lead["business_name"],
            lead["city"],
            lead["state"],
            lead["industry"],
            lead["website_url"],
            lead["email"],
            lead.get("phone", ""),
            results_data.get("overall_score", 0),
            results_data.get("grade", "N/A"),
            lead["created_at"]
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"}
    )


@app.get("/api/admin/export-all")
async def admin_export_all(admin_key: str = Query(default="")):
    """Export all leads (scanner + chatbot) as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Source", "Name", "Business Name", "Email", "Phone", "City", "State", "Industry", "Score", "Status", "Package", "Date"])

    scanner_leads = await get_all_leads(limit=10000, offset=0)
    for lead in scanner_leads:
        results_data = json.loads(lead["results"]) if lead.get("results") else {}
        writer.writerow([
            "Scanner", "", lead["business_name"], lead["email"],
            lead.get("phone", ""), lead["city"], lead["state"],
            lead["industry"], results_data.get("overall_score", 0),
            "complete", "", lead["created_at"]
        ])

    chat_leads = await get_chatbot_leads(limit=10000, offset=0)
    for lead in chat_leads:
        writer.writerow([
            "Chatbot", lead.get("name", ""), lead.get("business_name", ""),
            lead.get("email", ""), lead.get("phone", ""),
            "", "", lead.get("business_type", ""),
            "", lead.get("status", "new"),
            lead.get("recommended_package", ""), lead.get("created_at", "")
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=all-leads.csv"}
    )


# ═══════════════════════════════════════════════════════════════
# OUTREACH / PROSPECT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post("/api/outreach/analyze")
async def outreach_analyze(data: dict, admin_key: str = Query(default="")):
    """Analyze a single website for outreach."""
    url = data.get("url", "")
    if not url:
        return {"error": "URL is required"}
    if not url.startswith("http"):
        url = "https://" + url
    result = await analyze_website_quality(url)
    return result


@app.post("/api/outreach/scan-batch")
async def outreach_scan_batch(data: dict, admin_key: str = Query(default="")):
    """Scan multiple websites and find prospects."""
    websites = data.get("websites", [])
    if not websites:
        return {"error": "Provide a list of websites to scan"}
    results = await scan_prospect_websites(websites)

    saved_count = 0
    for result in results:
        if result["website_score"] < 70:
            await save_prospect(result)
            saved_count += 1

    return {
        "total_scanned": len(results),
        "prospects_found": saved_count,
        "results": results
    }


@app.get("/api/admin/prospects")
async def admin_prospects(
    admin_key: str = Query(default=""),
    limit: int = Query(default=50),
    offset: int = Query(default=0)
):
    """Get outreach prospects."""
    prospects = await get_prospects(limit, offset)
    for p in prospects:
        if p.get("issues") and isinstance(p["issues"], str):
            p["issues"] = json.loads(p["issues"])
    return {"prospects": prospects, "total": len(prospects)}


@app.post("/api/admin/prospects/{prospect_id}/status")
async def admin_update_prospect_status(prospect_id: str, data: dict, admin_key: str = Query(default="")):
    """Update a prospect's outreach status."""
    await update_prospect_status(prospect_id, data.get("status", "new"), data.get("notes", ""))
    return {"status": "updated"}


@app.get("/api/outreach/templates")
async def outreach_templates(admin_key: str = Query(default="")):
    """Get outreach email/SMS templates."""
    return {"templates": OUTREACH_TEMPLATES}


@app.post("/api/outreach/render-template")
async def outreach_render_template(data: dict, admin_key: str = Query(default="")):
    """Render an outreach template with variables."""
    template_name = data.get("template", "")
    variables = data.get("variables", {})
    template = get_outreach_template(template_name)
    if not template:
        return {"error": "Template not found"}

    if isinstance(template, dict):
        return {
            "subject": render_template(template.get("subject", ""), variables),
            "body": render_template(template.get("body", ""), variables)
        }
    else:
        return {"body": render_template(template, variables)}


# ═══════════════════════════════════════════════════════════════
# SETTINGS ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/admin/settings")
async def admin_get_settings(admin_key: str = Query(default="")):
    """Get chatbot/system settings."""
    greeting = await get_setting("chatbot_greeting", "Hi! I'm the AI assistant for Authority AI Systems. How can I help your business get recommended by AI?")
    scanner_url = await get_setting("scanner_url", "")
    notification_email = await get_setting("notification_email", NOTIFICATION_EMAIL)
    return {
        "chatbot_greeting": greeting,
        "scanner_url": scanner_url,
        "notification_email": notification_email
    }


@app.post("/api/admin/settings")
async def admin_update_settings(data: dict, admin_key: str = Query(default="")):
    """Update chatbot/system settings."""
    for key, value in data.items():
        if key in ("chatbot_greeting", "scanner_url", "notification_email"):
            await set_setting(key, value)
    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════════
# CLIENT REPORT ENDPOINT (public - shows problems, NOT solutions)
# ═══════════════════════════════════════════════════════════════

@app.get("/report/{scan_id}")
async def client_report(scan_id: str):
    """Generate client-facing report showing problems but NOT solutions."""
    scan = await get_scan(scan_id)
    if not scan or not scan.get("results"):
        return Response(content="<h1>Report not found</h1>", media_type="text/html", status_code=404)
    results = json.loads(scan["results"])
    scan_data = {
        "business_name": scan.get("business_name", ""),
        "city": scan.get("city", ""),
        "state": scan.get("state", ""),
        "industry": scan.get("industry", ""),
        "website_url": scan.get("website_url", ""),
        "email": scan.get("email", ""),
    }
    html = generate_report_html(scan_data, results)
    return Response(content=html, media_type="text/html")


# ═══════════════════════════════════════════════════════════════
# FULFILLMENT ADMIN ENDPOINTS (secret - step-by-step fix process)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/admin/clients")
async def admin_create_client(data: dict, admin_key: str = Query(default="")):
    """Convert a scan lead into a fulfillment client."""
    scan_id = data.get("scan_id", "")
    if not scan_id:
        raise HTTPException(status_code=400, detail="scan_id is required")
    scan = await get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    results = json.loads(scan["results"]) if scan.get("results") else {}
    client_data = {
        "business_name": scan.get("business_name", ""),
        "email": scan.get("email", ""),
        "phone": scan.get("phone", ""),
        "website_url": scan.get("website_url", ""),
        "city": scan.get("city", ""),
        "state": scan.get("state", ""),
        "industry": scan.get("industry", ""),
        "initial_score": results.get("overall_score", 0),
        "categories": results.get("categories", []),
        "package": data.get("package", ""),
        "monthly_rate": data.get("monthly_rate", 0),
    }
    client_id = await create_client(scan_id, client_data)
    return {"client_id": client_id, "status": "created"}


@app.get("/api/admin/clients")
async def admin_list_clients(
    admin_key: str = Query(default=""),
    status: str = Query(default=""),
    limit: int = Query(default=50),
    offset: int = Query(default=0)
):
    """List all fulfillment clients."""
    clients = await get_all_clients(status, limit, offset)
    return {"clients": clients, "total": len(clients)}


@app.get("/api/admin/clients/{client_id}")
async def admin_get_client(client_id: str, admin_key: str = Query(default="")):
    """Get a single client's details."""
    client = await get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.put("/api/admin/clients/{client_id}")
async def admin_update_client(client_id: str, data: dict, admin_key: str = Query(default="")):
    """Update client status, package, notes, etc."""
    await update_client(client_id, data)
    return {"status": "updated"}


@app.get("/api/admin/clients/{client_id}/tasks")
async def admin_get_tasks(
    client_id: str,
    admin_key: str = Query(default=""),
    status: str = Query(default="")
):
    """Get all tasks for a client."""
    tasks = await get_tasks(client_id, status)
    return {"tasks": tasks, "total": len(tasks)}


@app.post("/api/admin/clients/{client_id}/tasks")
async def admin_create_task(client_id: str, data: dict, admin_key: str = Query(default="")):
    """Create a new task for a client."""
    task_id = await create_task(client_id, data)
    return {"task_id": task_id, "status": "created"}


@app.put("/api/admin/tasks/{task_id}")
async def admin_update_task(task_id: str, data: dict, admin_key: str = Query(default="")):
    """Update a task's status, notes, etc."""
    await update_task(task_id, data)
    return {"status": "updated"}


@app.delete("/api/admin/tasks/{task_id}")
async def admin_delete_task(task_id: str, admin_key: str = Query(default="")):
    """Delete a task."""
    await delete_task(task_id)
    return {"status": "deleted"}


@app.get("/api/admin/clients/{client_id}/activity")
async def admin_get_activity(
    client_id: str,
    admin_key: str = Query(default=""),
    limit: int = Query(default=20)
):
    """Get activity log for a client."""
    activities = await get_activity(client_id, limit)
    return {"activities": activities}


@app.post("/api/admin/clients/{client_id}/rescan")
async def admin_rescan_client(client_id: str, background_tasks: BackgroundTasks, admin_key: str = Query(default="")):
    """Re-scan a client's website and update their score."""
    client = await get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    scan_data = {
        "business_name": client.get("business_name", ""),
        "website_url": client.get("website_url", ""),
        "city": client.get("city", ""),
        "state": client.get("state", ""),
        "industry": client.get("industry", ""),
        "email": client.get("email", ""),
    }
    scan_id = str(uuid.uuid4())
    await save_scan(scan_id, scan_data)
    background_tasks.add_task(process_scan, scan_id, scan_data)
    await log_activity(client_id, "rescan_started", f"New scan: {scan_id}")
    return {"scan_id": scan_id, "status": "processing"}


@app.get("/api/admin/fulfillment/stats")
async def admin_fulfillment_stats(admin_key: str = Query(default="")):
    """Get fulfillment dashboard stats."""
    stats = await get_fulfillment_stats()
    return stats


# ═══════════════════════════════════════════════════════════════
# AFFILIATE ENDPOINTS (public + admin)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/affiliate/apply")
async def affiliate_apply(data: dict):
    """Public endpoint for affiliate applications."""
    result = await apply_as_affiliate(data)
    if result.get("error"):
        return result
    return result


@app.post("/api/affiliate/login")
async def affiliate_login_endpoint(data: dict):
    """Affiliate login."""
    email = data.get("email", "")
    password = data.get("password", "")
    if not email or not password:
        return {"error": "Email and password are required"}
    result = await affiliate_login(email, password)
    return result


@app.get("/api/affiliate/{affiliate_id}/dashboard")
async def affiliate_dashboard_endpoint(affiliate_id: str):
    """Get affiliate dashboard data."""
    affiliate = await get_affiliate(affiliate_id)
    if not affiliate or affiliate.get("status") != "approved":
        return {"error": "Affiliate not found or not approved"}
    referrals = await get_affiliate_referrals(affiliate_id)
    payouts = await get_affiliate_payouts(affiliate_id)
    return {
        "affiliate": {
            "id": affiliate["id"],
            "name": affiliate["name"],
            "email": affiliate["email"],
            "referral_code": affiliate["referral_code"],
            "commission_rate": affiliate["commission_rate"],
            "total_referrals": affiliate["total_referrals"],
            "total_conversions": affiliate["total_conversions"],
            "total_earned": affiliate["total_earned"],
            "total_paid": affiliate["total_paid"],
            "balance": round(affiliate["total_earned"] - affiliate["total_paid"], 2),
        },
        "referrals": referrals,
        "payouts": payouts,
        "referral_link": f"https://authority-ai-scanner-1.onrender.com/?ref={affiliate['referral_code']}"
    }


@app.post("/api/affiliate/track")
async def affiliate_track(data: dict):
    """Track a referral when someone uses an affiliate link."""
    ref_code = data.get("ref", "")
    if not ref_code:
        return {"error": "Referral code required"}
    affiliate = await get_affiliate_by_code(ref_code)
    if not affiliate:
        return {"error": "Invalid referral code"}
    referral_id = await track_referral(
        affiliate["id"],
        scan_id=data.get("scan_id", ""),
        lead_email=data.get("email", ""),
        lead_business=data.get("business_name", "")
    )
    return {"referral_id": referral_id, "affiliate_name": affiliate["name"]}


# ── Admin Affiliate Management ────────────────────────────────

@app.get("/api/admin/affiliates")
async def admin_list_affiliates(
    admin_key: str = Query(default=""),
    status: str = Query(default=""),
    limit: int = Query(default=50)
):
    """List all affiliates."""
    affiliates = await get_all_affiliates(status, limit)
    return {"affiliates": affiliates, "total": len(affiliates)}


@app.get("/api/admin/affiliates/stats")
async def admin_affiliate_stats_endpoint(admin_key: str = Query(default="")):
    """Get affiliate program stats."""
    stats = await get_affiliate_stats()
    return stats


@app.get("/api/admin/affiliates/{affiliate_id}")
async def admin_get_affiliate(affiliate_id: str, admin_key: str = Query(default="")):
    """Get a single affiliate's details."""
    affiliate = await get_affiliate(affiliate_id)
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    referrals = await get_affiliate_referrals(affiliate_id)
    payouts = await get_affiliate_payouts(affiliate_id)
    return {"affiliate": affiliate, "referrals": referrals, "payouts": payouts}


@app.post("/api/admin/affiliates/{affiliate_id}/approve")
async def admin_approve_affiliate(affiliate_id: str, admin_key: str = Query(default="")):
    """Approve an affiliate application."""
    result = await approve_affiliate(affiliate_id)
    return {"status": "approved", "affiliate": result}


@app.post("/api/admin/affiliates/{affiliate_id}/reject")
async def admin_reject_affiliate(affiliate_id: str, data: dict = {}, admin_key: str = Query(default="")):
    """Reject an affiliate application."""
    reason = data.get("reason", "") if isinstance(data, dict) else ""
    result = await reject_affiliate(affiliate_id, reason)
    return result


@app.put("/api/admin/affiliates/{affiliate_id}")
async def admin_update_affiliate(affiliate_id: str, data: dict, admin_key: str = Query(default="")):
    """Update affiliate details."""
    await update_affiliate(affiliate_id, data)
    return {"status": "updated"}


@app.post("/api/admin/affiliates/{affiliate_id}/payout")
async def admin_record_payout(affiliate_id: str, data: dict, admin_key: str = Query(default="")):
    """Record a payout to an affiliate."""
    amount = data.get("amount", 0)
    if not amount:
        raise HTTPException(status_code=400, detail="Amount is required")
    payout_id = await record_payout(
        affiliate_id, amount,
        period=data.get("period", ""),
        method=data.get("method", ""),
        notes=data.get("notes", "")
    )
    return {"payout_id": payout_id, "status": "recorded"}


@app.get("/api/admin/affiliates/{affiliate_id}/referrals")
async def admin_get_affiliate_referrals(affiliate_id: str, admin_key: str = Query(default="")):
    """Get all referrals for an affiliate."""
    referrals = await get_affiliate_referrals(affiliate_id)
    return {"referrals": referrals, "total": len(referrals)}


@app.post("/api/admin/referrals/{referral_id}/convert")
async def admin_convert_referral(referral_id: str, data: dict, admin_key: str = Query(default="")):
    """Mark a referral as converted (client signed up)."""
    package = data.get("package", "")
    monthly_rate = data.get("monthly_rate", 0)
    commission_rate = data.get("commission_rate", 0.20)
    if not package or not monthly_rate:
        raise HTTPException(status_code=400, detail="Package and monthly_rate are required")
    await convert_referral(referral_id, package, monthly_rate, commission_rate)
    return {"status": "converted"}


# ═══════════════════════════════════════════════════════════════
# SERVE FRONTEND STATIC FILES
# ═══════════════════════════════════════════════════════════════

STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
