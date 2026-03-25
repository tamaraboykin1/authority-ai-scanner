import aiosqlite
import os
import json
from datetime import datetime

_default_db = "/data/app.db" if os.path.isdir("/data") else os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")
DB_PATH = os.environ.get("DB_PATH", _default_db)


async def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                business_name TEXT NOT NULL,
                contact_name TEXT,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                industry TEXT NOT NULL,
                website_url TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                status TEXT DEFAULT 'processing',
                results TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Add contact_name column if it doesn't exist (migration for existing DBs)
        try:
            await db.execute("ALTER TABLE scans ADD COLUMN contact_name TEXT")
            await db.commit()
        except Exception:
            pass  # Column already exists
        await db.commit()
    finally:
        await db.close()


async def save_scan(scan_id: str, data: dict):
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO scans (id, business_name, contact_name, city, state, industry, website_url, email, phone, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'processing')""",
            (scan_id, data["business_name"], data.get("contact_name", ""), data["city"], data["state"],
             data["industry"], data["website_url"], data["email"], data.get("phone", ""))
        )
        await db.commit()
    finally:
        await db.close()


async def update_scan_results(scan_id: str, results: dict):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE scans SET status = 'complete', results = ? WHERE id = ?",
            (json.dumps(results), scan_id)
        )
        await db.commit()
    finally:
        await db.close()


async def update_scan_error(scan_id: str, error: str):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE scans SET status = 'error', results = ? WHERE id = ?",
            (json.dumps({"error": error}), scan_id)
        )
        await db.commit()
    finally:
        await db.close()


async def get_scan(scan_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await db.close()


async def get_scan_by_email(email: str):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM scans WHERE email = ? AND status IN ('complete', 'processing') ORDER BY created_at DESC LIMIT 1",
            (email,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await db.close()


async def get_all_leads(limit: int = 50, offset: int = 0):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM scans WHERE status = 'complete' ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_stats():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) as total FROM scans WHERE status = 'complete'")
        row = await cursor.fetchone()
        total = dict(row)["total"] if row else 0

        cursor = await db.execute(
            "SELECT COUNT(*) as today FROM scans WHERE status = 'complete' AND date(created_at) = date('now')"
        )
        row = await cursor.fetchone()
        today = dict(row)["today"] if row else 0

        cursor = await db.execute(
            "SELECT AVG(json_extract(results, '$.overall_score')) as avg_score FROM scans WHERE status = 'complete' AND results IS NOT NULL"
        )
        row = await cursor.fetchone()
        avg_score = round(dict(row)["avg_score"] or 0, 1)

        return {"total_scans": total, "scans_today": today, "average_score": avg_score}
    finally:
        await db.close()
