"""Lead management module — chatbot leads, follow-ups, outreach prospects."""
import json
import os
import uuid
from datetime import datetime

import aiosqlite

from app.database import get_db, DB_PATH


async def init_leads_db():
    """Create tables for chatbot leads, conversations, follow-ups, and prospects."""
    db = await get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_leads (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                business_name TEXT,
                business_type TEXT,
                challenge TEXT,
                budget TEXT,
                recommended_package TEXT,
                source TEXT DEFAULT 'chatbot',
                status TEXT DEFAULT 'new',
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS follow_ups (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                lead_type TEXT DEFAULT 'chatbot',
                step INTEGER DEFAULT 1,
                subject TEXT,
                body TEXT,
                status TEXT DEFAULT 'pending',
                scheduled_at TEXT,
                sent_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS outreach_prospects (
                id TEXT PRIMARY KEY,
                business_name TEXT,
                website_url TEXT,
                email TEXT,
                phone TEXT,
                city TEXT,
                state TEXT,
                industry TEXT,
                website_score INTEGER,
                issues TEXT,
                outreach_status TEXT DEFAULT 'new',
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()
    finally:
        await db.close()


# ─── Chatbot Leads ───

async def save_chatbot_lead(lead_data: dict) -> str:
    """Save a qualified lead from the chatbot."""
    lead_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO chatbot_leads (id, name, email, phone, business_name, business_type, challenge, budget, recommended_package, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (lead_id, lead_data.get("name", ""), lead_data.get("email", ""),
             lead_data.get("phone", ""), lead_data.get("business_name", ""),
             lead_data.get("business_type", ""), lead_data.get("challenge", ""),
             lead_data.get("budget", ""), lead_data.get("recommended_package", ""),
             lead_data.get("source", "chatbot"))
        )
        await db.commit()
    finally:
        await db.close()
    return lead_id


async def get_chatbot_leads(limit: int = 50, offset: int = 0) -> list:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM chatbot_leads ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_chatbot_lead(lead_id: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM chatbot_leads WHERE id = ?", (lead_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def update_lead_status(lead_id: str, status: str, notes: str = ""):
    db = await get_db()
    try:
        if notes:
            await db.execute(
                "UPDATE chatbot_leads SET status = ?, notes = ? WHERE id = ?",
                (status, notes, lead_id)
            )
        else:
            await db.execute(
                "UPDATE chatbot_leads SET status = ? WHERE id = ?",
                (status, lead_id)
            )
        await db.commit()
    finally:
        await db.close()


# ─── Conversations ───

async def save_message(session_id: str, role: str, content: str):
    msg_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO conversations (id, session_id, role, content) VALUES (?, ?, ?, ?)",
            (msg_id, session_id, role, content)
        )
        await db.commit()
    finally:
        await db.close()


async def get_conversation(session_id: str) -> list:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT role, content, created_at FROM conversations WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_all_conversations(limit: int = 50) -> list:
    """Get unique conversation sessions with latest message."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT session_id, 
                   COUNT(*) as message_count,
                   MIN(created_at) as started_at,
                   MAX(created_at) as last_message_at
            FROM conversations 
            GROUP BY session_id 
            ORDER BY MAX(created_at) DESC 
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


# ─── Follow-ups ───

async def create_follow_up(lead_id: str, lead_type: str, step: int, subject: str, body: str, scheduled_at: str = ""):
    fu_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO follow_ups (id, lead_id, lead_type, step, subject, body, scheduled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fu_id, lead_id, lead_type, step, subject, body, scheduled_at or datetime.utcnow().isoformat())
        )
        await db.commit()
    finally:
        await db.close()
    return fu_id


async def get_follow_ups(lead_id: str = "", status: str = "") -> list:
    db = await get_db()
    try:
        query = "SELECT * FROM follow_ups"
        params = []
        conditions = []
        if lead_id:
            conditions.append("lead_id = ?")
            params.append(lead_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC"
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def mark_follow_up_sent(fu_id: str):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE follow_ups SET status = 'sent', sent_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), fu_id)
        )
        await db.commit()
    finally:
        await db.close()


# ─── Outreach Prospects ───

async def save_prospect(prospect_data: dict) -> str:
    prospect_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO outreach_prospects (id, business_name, website_url, email, phone, city, state, industry, website_score, issues)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (prospect_id, prospect_data.get("business_name", ""),
             prospect_data.get("website_url", ""), prospect_data.get("email", ""),
             prospect_data.get("phone", ""), prospect_data.get("city", ""),
             prospect_data.get("state", ""), prospect_data.get("industry", ""),
             prospect_data.get("website_score", 0),
             json.dumps(prospect_data.get("issues", [])))
        )
        await db.commit()
    finally:
        await db.close()
    return prospect_id


async def get_prospects(limit: int = 50, offset: int = 0) -> list:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM outreach_prospects ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def update_prospect_status(prospect_id: str, status: str, notes: str = ""):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE outreach_prospects SET outreach_status = ?, notes = ? WHERE id = ?",
            (status, notes, prospect_id)
        )
        await db.commit()
    finally:
        await db.close()


# ─── Chatbot Settings ───

async def get_setting(key: str, default: str = "") -> str:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT value FROM chatbot_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return dict(row)["value"] if row else default
    finally:
        await db.close()


async def set_setting(key: str, value: str):
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO chatbot_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()
    finally:
        await db.close()


# ─── Combined Stats ───

async def get_dashboard_stats() -> dict:
    db = await get_db()
    try:
        # Scanner leads
        cursor = await db.execute("SELECT COUNT(*) as total FROM scans WHERE status = 'complete'")
        row = await cursor.fetchone()
        scanner_leads = dict(row)["total"] if row else 0

        # Chatbot leads
        cursor = await db.execute("SELECT COUNT(*) as total FROM chatbot_leads")
        row = await cursor.fetchone()
        chatbot_leads = dict(row)["total"] if row else 0

        # Chatbot leads by status
        cursor = await db.execute(
            "SELECT status, COUNT(*) as count FROM chatbot_leads GROUP BY status"
        )
        rows = await cursor.fetchall()
        leads_by_status = {dict(r)["status"]: dict(r)["count"] for r in rows}

        # Conversations today
        cursor = await db.execute(
            "SELECT COUNT(DISTINCT session_id) as count FROM conversations WHERE date(created_at) = date('now')"
        )
        row = await cursor.fetchone()
        conversations_today = dict(row)["count"] if row else 0

        # Prospects
        cursor = await db.execute("SELECT COUNT(*) as total FROM outreach_prospects")
        row = await cursor.fetchone()
        total_prospects = dict(row)["total"] if row else 0

        # Pending follow-ups
        cursor = await db.execute("SELECT COUNT(*) as total FROM follow_ups WHERE status = 'pending'")
        row = await cursor.fetchone()
        pending_follow_ups = dict(row)["total"] if row else 0

        return {
            "scanner_leads": scanner_leads,
            "chatbot_leads": chatbot_leads,
            "leads_by_status": leads_by_status,
            "conversations_today": conversations_today,
            "total_prospects": total_prospects,
            "pending_follow_ups": pending_follow_ups,
            "total_leads": scanner_leads + chatbot_leads
        }
    finally:
        await db.close()
