"""Email sending module for automated follow-ups and notifications."""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# SMTP Configuration from environment
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER)
FROM_NAME = os.environ.get("FROM_NAME", "Authority AI Systems")


def is_email_configured() -> bool:
    """Check if SMTP email is configured."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def send_email(to_email: str, subject: str, body: str, html_body: str = "") -> dict:
    """Send an email via SMTP.
    
    Returns dict with 'success' bool and 'error' string if failed.
    """
    if not is_email_configured():
        return {"success": False, "error": "Email not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS env vars."}

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Reply-To"] = FROM_EMAIL

        # Plain text version
        msg.attach(MIMEText(body, "plain"))

        # HTML version (if provided)
        if html_body:
            msg.attach(MIMEText(html_body, "html"))
        else:
            # Convert plain text to simple HTML
            html = body.replace("\n\n", "</p><p>").replace("\n", "<br>")
            html = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1e293b;">
                <div style="border-bottom: 3px solid #f97316; padding-bottom: 16px; margin-bottom: 24px;">
                    <h2 style="margin: 0; color: #f97316; font-size: 20px;">Authority AI Systems</h2>
                </div>
                <p>{html}</p>
                <div style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8;">
                    <p>Authority AI Systems — Making Businesses Visible to AI</p>
                    <p><a href="https://authorityaisystems.com" style="color: #f97316;">authorityaisystems.com</a></p>
                </div>
            </div>
            """
            msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}: {subject}")
        return {"success": True, "error": ""}

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP auth error: {e}")
        return {"success": False, "error": f"Authentication failed: {str(e)}"}
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending to {to_email}: {e}")
        return {"success": False, "error": f"SMTP error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return {"success": False, "error": str(e)}


def send_lead_notification(lead_data: dict) -> dict:
    """Send internal notification when a new lead comes in."""
    notification_email = os.environ.get("NOTIFICATION_EMAIL", "")
    if not notification_email or not is_email_configured():
        return {"success": False, "error": "Notification email not configured"}

    name = lead_data.get("name", "Unknown")
    business = lead_data.get("business_name", "Unknown")
    email = lead_data.get("email", "N/A")
    phone = lead_data.get("phone", "N/A")
    source = lead_data.get("source", "chatbot")
    package = lead_data.get("recommended_package", "N/A")

    subject = f"New Lead: {business} ({source})"
    body = f"""NEW LEAD ALERT

Name: {name}
Business: {business}
Email: {email}
Phone: {phone}
Source: {source}
Recommended Package: {package}
Challenge: {lead_data.get('challenge', 'N/A')}
Budget: {lead_data.get('budget', 'N/A')}

---
This lead has been added to your dashboard automatically.
Follow-up emails have been queued.

View dashboard: https://live-scanner-app-3t5y1ivp.devinapps.com
"""
    return send_email(notification_email, subject, body)
