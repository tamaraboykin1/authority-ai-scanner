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

load_dotenv()

ADMIN_KEY = os.environ.get("ADMIN_KEY", "a7x9k2m4")
AUTH_USER = os.environ.get("AUTH_USER", "")
AUTH_PASS = os.environ.get("AUTH_PASS", "")
NOTIFICATION_EMAIL = os.environ.get("NOTIFICATION_EMAIL", "")


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not AUTH_USER or not AUTH_PASS:
            return await call_next(request)
        # Allow public endpoints without auth
        public_paths = ("/healthz", "/", "/index.html")
        public_prefixes = ("/api/chat", "/api/scan", "/assets/", "/static/", "/chatbot-widget.js")
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
