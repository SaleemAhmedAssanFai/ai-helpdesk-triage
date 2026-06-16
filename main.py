"""
AI Help Desk Triage Assistant — Main Pipeline
Runs the full triage loop: fetch tickets → AI analysis → post results.
"""
import json, logging, time
from datetime import datetime
from pathlib import Path

from triage_engine       import triage_ticket
from osticket_connector  import get_open_tickets, get_ticket_detail, post_internal_note
from auto_responder      import send_auto_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/triage.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)
LOG_FILE = Path("logs/triage_results.json")

def load_processed() -> set:
    "Load set of already-processed ticket IDs to avoid duplicates."
    if not LOG_FILE.exists(): return set()
    with open(LOG_FILE) as f:
        try:
            data = json.load(f)
            return {r["ticket_id"] for r in data}
        except: return set()

def save_result(result: dict):
    "Append a triage result to the JSON log file."
    existing = []
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            try: existing = json.load(f)
            except: existing = []
    existing.append(result)
    with open(LOG_FILE, "w") as f:
        json.dump(existing, f, indent=2)

def run_pipeline():
    log.info("═══ Starting AI Triage Pipeline ═══")
    processed = load_processed()
    tickets   = get_open_tickets()

    if not tickets:
        log.info("No open tickets found.")
        return

    new_tickets = [t for t in tickets if str(t.get("id")) not in processed]
    log.info(f"Found {len(tickets)} tickets, {len(new_tickets)} unprocessed")

    for ticket in new_tickets:
        ticket_id = str(ticket.get("id"))
        subject   = ticket.get("subject", "No subject")
        user_name = ticket.get("name", "User")

        # Get full ticket detail for the description
        detail      = get_ticket_detail(ticket_id)
        description = detail.get("description", subject)

        # Run AI triage
        result = triage_ticket(ticket_id, subject, description, user_name)

        if result["status"] == "success":
            result["processed_at"] = datetime.now().isoformat()
            result["subject"]      = subject
            result["user_name"]    = user_name

            post_internal_note(ticket_id, result)
            send_auto_response(ticket_id, result)
            save_result(result)
            log.info(f"✓ Ticket {ticket_id} fully processed")
        else:
            log.error(f"✗ Triage failed for ticket {ticket_id}")

        time.sleep(1)   # be polite to the APIs

    log.info(f"═══ Pipeline complete. Processed {len(new_tickets)} tickets. ═══")

if __name__ == "__main__":
    run_pipeline()
