"""Affiliate system for managing sales representatives and referral tracking."""
import json
import uuid
import secrets
import string
from datetime import datetime

from app.database import get_db


async def init_affiliates_db():
    """Create affiliate tables."""
    db = await get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS affiliates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT DEFAULT '',
                referral_code TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                commission_rate REAL DEFAULT 0.20,
                total_referrals INTEGER DEFAULT 0,
                total_conversions INTEGER DEFAULT 0,
                total_earned REAL DEFAULT 0,
                total_paid REAL DEFAULT 0,
                bio TEXT DEFAULT '',
                password_hash TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                approved_at TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id TEXT PRIMARY KEY,
                affiliate_id TEXT NOT NULL,
                scan_id TEXT DEFAULT '',
                lead_email TEXT DEFAULT '',
                lead_business TEXT DEFAULT '',
                status TEXT DEFAULT 'clicked',
                package TEXT DEFAULT '',
                monthly_rate REAL DEFAULT 0,
                commission_amount REAL DEFAULT 0,
                months_paid INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                converted_at TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                FOREIGN KEY (affiliate_id) REFERENCES affiliates (id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS affiliate_payouts (
                id TEXT PRIMARY KEY,
                affiliate_id TEXT NOT NULL,
                amount REAL NOT NULL,
                period TEXT DEFAULT '',
                method TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (affiliate_id) REFERENCES affiliates (id)
            )
        """)
        await db.commit()
    finally:
        await db.close()


def _generate_referral_code(name: str) -> str:
    """Generate a unique referral code like JOHN4X7."""
    first = name.strip().split()[0].upper()[:4] if name.strip() else "REF"
    suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(3))
    return f"{first}{suffix}"


# ── Affiliate Signup & Management ──────────────────────────────

async def apply_as_affiliate(data: dict) -> dict:
    """Submit a sales team application with full application data."""
    affiliate_id = str(uuid.uuid4())
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    bio = data.get("bio", "").strip()

    if not name or not email:
        return {"error": "Name and email are required"}

    # Build extended application data as JSON stored in bio field
    application_info = {
        "city": data.get("city", "").strip(),
        "state": data.get("state", "").strip(),
        "employment_status": data.get("employment_status", "").strip(),
        "sales_experience": data.get("sales_experience", "").strip(),
        "industry_experience": data.get("industry_experience", "").strip(),
        "why_join": data.get("why_join", "").strip(),
        "lead_generation_plan": data.get("lead_generation_plan", "").strip(),
        "linkedin": data.get("linkedin", "").strip(),
        "availability": data.get("availability", "").strip(),
        "how_heard": data.get("how_heard", "").strip(),
        "previous_experience": bio,
    }
    bio_json = json.dumps(application_info)

    # Check if email already registered
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id, status FROM affiliates WHERE email = ?", (email,))
        existing = await cursor.fetchone()
        if existing:
            row = dict(existing)
            if row["status"] == "pending":
                return {"error": "Application already submitted and pending review"}
            elif row["status"] == "approved":
                return {"error": "You are already an approved team member", "affiliate_id": row["id"]}
            elif row["status"] == "rejected":
                return {"error": "Your previous application was not approved. Contact us for more info."}

        # Generate unique referral code
        referral_code = _generate_referral_code(name)
        # Make sure it's unique
        cursor = await db.execute("SELECT id FROM affiliates WHERE referral_code = ?", (referral_code,))
        while await cursor.fetchone():
            referral_code = _generate_referral_code(name)
            cursor = await db.execute("SELECT id FROM affiliates WHERE referral_code = ?", (referral_code,))

        # Simple password for affiliate login (they can change later)
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

        await db.execute(
            """INSERT INTO affiliates (id, name, email, phone, referral_code, status, bio, password_hash)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (affiliate_id, name, email, phone, referral_code, bio_json, temp_password)
        )
        await db.commit()
        return {
            "affiliate_id": affiliate_id,
            "referral_code": referral_code,
            "status": "pending",
            "message": "Application submitted! We'll review your application and get back to you within 24-48 hours."
        }
    finally:
        await db.close()


async def get_affiliate(affiliate_id: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM affiliates WHERE id = ?", (affiliate_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}
    finally:
        await db.close()


async def get_affiliate_by_code(referral_code: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM affiliates WHERE referral_code = ? AND status = 'approved'",
            (referral_code,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}
    finally:
        await db.close()


async def get_affiliate_by_email(email: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM affiliates WHERE email = ?", (email.lower(),))
        row = await cursor.fetchone()
        return dict(row) if row else {}
    finally:
        await db.close()


async def affiliate_login(email: str, password: str) -> dict:
    """Authenticate an affiliate."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM affiliates WHERE email = ? AND status = 'approved'",
            (email.lower(),)
        )
        row = await cursor.fetchone()
        if not row:
            return {"error": "Invalid credentials or account not approved"}
        affiliate = dict(row)
        if affiliate.get("password_hash") != password:
            return {"error": "Invalid credentials"}
        # Return safe data (no password)
        return {
            "affiliate_id": affiliate["id"],
            "name": affiliate["name"],
            "email": affiliate["email"],
            "referral_code": affiliate["referral_code"],
            "status": affiliate["status"],
            "commission_rate": affiliate["commission_rate"],
            "total_referrals": affiliate["total_referrals"],
            "total_conversions": affiliate["total_conversions"],
            "total_earned": affiliate["total_earned"],
            "total_paid": affiliate["total_paid"],
        }
    finally:
        await db.close()


async def get_all_affiliates(status: str = "", limit: int = 50) -> list:
    db = await get_db()
    try:
        if status:
            cursor = await db.execute(
                "SELECT * FROM affiliates WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM affiliates ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def approve_affiliate(affiliate_id: str) -> dict:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE affiliates SET status = 'approved', approved_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), affiliate_id)
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM affiliates WHERE id = ?", (affiliate_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}
    finally:
        await db.close()


async def reject_affiliate(affiliate_id: str, reason: str = "") -> dict:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE affiliates SET status = 'rejected', notes = ? WHERE id = ?",
            (reason, affiliate_id)
        )
        await db.commit()
        return {"status": "rejected"}
    finally:
        await db.close()


async def update_affiliate(affiliate_id: str, data: dict):
    db = await get_db()
    try:
        allowed = ["name", "phone", "commission_rate", "notes", "password_hash", "status"]
        sets = []
        vals = []
        for key in allowed:
            if key in data:
                sets.append(f"{key} = ?")
                vals.append(data[key])
        if sets:
            vals.append(affiliate_id)
            await db.execute(f"UPDATE affiliates SET {', '.join(sets)} WHERE id = ?", tuple(vals))
            await db.commit()
    finally:
        await db.close()


# ── Referral Tracking ─────────────────────────────────────────

async def track_referral(affiliate_id: str, scan_id: str = "", lead_email: str = "", lead_business: str = "") -> str:
    """Track a referral click/scan from an affiliate link."""
    referral_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO referrals (id, affiliate_id, scan_id, lead_email, lead_business, status)
               VALUES (?, ?, ?, ?, ?, 'clicked')""",
            (referral_id, affiliate_id, scan_id, lead_email, lead_business)
        )
        # Increment referral count
        await db.execute(
            "UPDATE affiliates SET total_referrals = total_referrals + 1 WHERE id = ?",
            (affiliate_id,)
        )
        await db.commit()
        return referral_id
    finally:
        await db.close()


async def convert_referral(referral_id: str, package: str, monthly_rate: float, commission_rate: float = 0.20):
    """Mark a referral as converted (client signed up)."""
    db = await get_db()
    try:
        commission = monthly_rate * commission_rate
        await db.execute(
            """UPDATE referrals SET status = 'converted', package = ?, monthly_rate = ?,
               commission_amount = ?, converted_at = ? WHERE id = ?""",
            (package, monthly_rate, commission, datetime.utcnow().isoformat(), referral_id)
        )
        # Get affiliate_id and update their stats
        cursor = await db.execute("SELECT affiliate_id FROM referrals WHERE id = ?", (referral_id,))
        row = await cursor.fetchone()
        if row:
            affiliate_id = dict(row)["affiliate_id"]
            await db.execute(
                """UPDATE affiliates SET total_conversions = total_conversions + 1,
                   total_earned = total_earned + ? WHERE id = ?""",
                (commission, affiliate_id)
            )
        await db.commit()
    finally:
        await db.close()


async def get_affiliate_referrals(affiliate_id: str, limit: int = 50) -> list:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM referrals WHERE affiliate_id = ? ORDER BY created_at DESC LIMIT ?",
            (affiliate_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_referral_by_scan(scan_id: str) -> dict:
    """Find a referral by scan ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM referrals WHERE scan_id = ?", (scan_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}
    finally:
        await db.close()


# ── Payouts ───────────────────────────────────────────────────

async def record_payout(affiliate_id: str, amount: float, period: str = "", method: str = "", notes: str = "") -> str:
    payout_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO affiliate_payouts (id, affiliate_id, amount, period, method, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (payout_id, affiliate_id, amount, period, method, notes)
        )
        await db.execute(
            "UPDATE affiliates SET total_paid = total_paid + ? WHERE id = ?",
            (amount, affiliate_id)
        )
        await db.commit()
        return payout_id
    finally:
        await db.close()


async def get_affiliate_payouts(affiliate_id: str, limit: int = 50) -> list:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM affiliate_payouts WHERE affiliate_id = ? ORDER BY created_at DESC LIMIT ?",
            (affiliate_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


# ── Affiliate Stats ───────────────────────────────────────────

async def get_affiliate_stats() -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) as c FROM affiliates")
        total = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT COUNT(*) as c FROM affiliates WHERE status = 'approved'")
        approved = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT COUNT(*) as c FROM affiliates WHERE status = 'pending'")
        pending = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT COUNT(*) as c FROM referrals WHERE status = 'converted'")
        conversions = dict(await cursor.fetchone())["c"]

        cursor = await db.execute("SELECT SUM(total_earned) as s FROM affiliates")
        row = await cursor.fetchone()
        total_commissions = dict(row)["s"] or 0

        cursor = await db.execute("SELECT SUM(total_paid) as s FROM affiliates")
        row = await cursor.fetchone()
        total_paid = dict(row)["s"] or 0

        return {
            "total_affiliates": total,
            "approved_affiliates": approved,
            "pending_applications": pending,
            "total_conversions": conversions,
            "total_commissions_earned": round(total_commissions, 2),
            "total_commissions_paid": round(total_paid, 2),
            "outstanding_balance": round(total_commissions - total_paid, 2)
        }
    finally:
        await db.close()
