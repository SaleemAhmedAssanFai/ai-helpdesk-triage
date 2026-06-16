"""
Auto Responder — posts AI draft reply directly via MySQL.
Skips SEV-1 and SEV-2 (human review required).
"""
import os, logging
import pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

DB = dict(
    host   = os.getenv("DB_HOST", "127.0.0.1"),
    user   = os.getenv("DB_USER", "osticket_user"),
    passwd = os.getenv("DB_PASS", "StrongPass123!"),
    db     = os.getenv("DB_NAME", "osticket"),
    charset= "utf8mb4",
)

HUMAN_REVIEW_REQUIRED = {"SEV-1", "SEV-2"}

def _conn():
    return pymysql.connect(**DB, cursorclass=pymysql.cursors.DictCursor)

def get_thread_id(ticket_id: str) -> int:
    try:
        with _conn() as con:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT id FROM ost_thread
                    WHERE object_id = %s AND object_type = 'T' LIMIT 1
                """, (ticket_id,))
                row = cur.fetchone()
                return row["id"] if row else None
    except Exception as e:
        log.error(f"Failed to get thread_id: {e}")
        return None

def send_auto_response(ticket_id: str, triage_result: dict) -> bool:
    priority = triage_result.get("priority", "SEV-4")

    if priority in HUMAN_REVIEW_REQUIRED:
        log.info(f"Ticket {ticket_id} is {priority} — skipping auto-response, human review required.")
        return False

    draft = triage_result.get("draft_response", "")
    if not draft:
        log.warning(f"No draft response for ticket {ticket_id}")
        return False

    footer = (
        "\n\n---\n"
        "This is an automated first response. "
        "A member of our support team will follow up personally."
    )
    body = draft + footer

    thread_id = get_thread_id(ticket_id)
    if not thread_id:
        log.error(f"No thread found for ticket {ticket_id}")
        return False

    try:
        with _conn() as con:
            with con.cursor() as cur:
                cur.execute("""
                    INSERT INTO ost_thread_entry
                        (thread_id, staff_id, type, flags, title, body, format, created, updated)
                    VALUES (%s, 0, 'R', 0, %s, %s, 'text', NOW(), NOW())
                """, (thread_id, "Thank you for contacting IT Support", body))
                con.commit()
                log.info(f"Auto-response posted to ticket {ticket_id} (priority: {priority})")
                return True
    except Exception as e:
        log.error(f"Auto-response failed for ticket {ticket_id}: {e}")
        return False
