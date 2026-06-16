import os, logging, re
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

def _conn():
    return pymysql.connect(**DB, cursorclass=pymysql.cursors.DictCursor)

def get_open_tickets() -> list:
    try:
        with _conn() as con:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT t.ticket_id AS id, u.name, ue.address AS email, t.created
                    FROM ost_ticket t
                    JOIN ost_user u        ON u.id = t.user_id
                    JOIN ost_user_email ue ON ue.user_id = u.id
                    WHERE t.status_id = 1
                    ORDER BY t.created DESC LIMIT 50
                """)
                tickets = cur.fetchall()
                for t in tickets:
                    if isinstance(t.get("created"), datetime):
                        t["created"] = t["created"].isoformat()
                log.info(f"Fetched {len(tickets)} open tickets from DB")
                return tickets
    except Exception as e:
        log.error(f"Failed to fetch tickets: {e}")
        return []

def get_ticket_detail(ticket_id: str) -> dict:
    try:
        with _conn() as con:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT th.id AS thread_id, te.title AS subject, te.body AS description
                    FROM ost_thread th
                    JOIN ost_thread_entry te ON te.thread_id = th.id
                    WHERE th.object_id = %s AND th.object_type = 'T' AND te.type = 'M'
                    ORDER BY te.created ASC LIMIT 1
                """, (ticket_id,))
                row = cur.fetchone()
                if row:
                    body = re.sub(r'<[^>]+>', ' ', row["description"] or "")
                    return {"subject": row["subject"] or "No subject",
                            "description": body.strip(), "thread_id": row["thread_id"]}
                return {}
    except Exception as e:
        log.error(f"Failed to get ticket detail {ticket_id}: {e}")
        return {}

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
        log.error(f"Failed to get thread_id for {ticket_id}: {e}")
        return None

def post_internal_note(ticket_id: str, triage_result: dict) -> bool:
    p = triage_result
    note = f"""AI TRIAGE ANALYSIS — AUTO-GENERATED
Model: LLaMA 3 70B via Groq API
Analysed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Confidence: {int(p.get('confidence', 0) * 100)}%

PRIORITY:   {p.get('priority', 'Unknown')}
DEPARTMENT: {p.get('department', 'Unknown')}
ESCALATE:   {'YES' if p.get('escalate') else 'No'}
ETA:        {p.get('estimated_resolution', 'Unknown')}

ROOT CAUSE:
{p.get('root_cause', 'Not determined')}

URGENCY REASON:
{p.get('urgency_reason', 'Not provided')}

SUGGESTED FIRST RESPONSE:
{p.get('draft_response', 'No draft generated')}

This analysis is AI-generated. Always verify before acting."""

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
                    VALUES (%s, 0, 'N', 0, %s, %s, 'text', NOW(), NOW())
                """, (thread_id, "AI Triage Analysis", note))
                con.commit()
                log.info(f"Posted internal note to ticket {ticket_id}")
                return True
    except Exception as e:
        log.error(f"Failed to post note to ticket {ticket_id}: {e}")
        return False
