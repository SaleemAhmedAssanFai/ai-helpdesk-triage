"""
AI Triage Engine
Sends ticket data to LLaMA 3 via Groq API and returns
structured triage decisions in JSON format.
"""
import os, json, logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are an expert IT Help Desk Triage Analyst with 10 years of experience
in enterprise IT support. Your job is to analyse incoming support tickets
and return a structured triage decision.

You MUST respond with ONLY valid JSON — no explanation, no markdown,
no code blocks. Just the raw JSON object.

JSON format:
{
  "priority": "SEV-1" | "SEV-2" | "SEV-3" | "SEV-4" | "SEV-5",
  "department": "IT Support" | "Networking" | "HR" | "Security" | "Maintenance",
  "confidence": 0.0 to 1.0,
  "root_cause": "Brief guess at what is causing this issue",
  "urgency_reason": "One sentence explaining why you assigned this priority",
  "draft_response": "A professional, empathetic first-response message to send to the user. Use their name if provided. Sign off as IT Support Team.",
  "escalate": true | false,
  "escalation_reason": "Reason if escalate is true, else empty string",
  "estimated_resolution": "e.g. 15 minutes | 1 hour | 4 hours | next business day"
}

Priority guide:
SEV-1: Complete outage, security breach, no one can work — respond in 1 hour
SEV-2: Single user/team fully blocked, significant business impact — respond in 4 hours
SEV-3: Degraded service, workaround exists — respond in 8 hours
SEV-4: Minor issue, low business impact — respond in 24 hours
SEV-5: General request, enhancement, question — respond in 72 hours
"""

def triage_ticket(ticket_id: str, subject: str, description: str,
                  user_name: str = "User") -> dict:
    """
    Send a ticket to LLaMA 3 for AI triage analysis.
    Returns a dict with priority, department, draft response, etc.
    """
    user_message = f"""
Ticket ID: {ticket_id}
Submitted by: {user_name}
Subject: {subject}
Description: {description}

Analyse this ticket and return your triage decision as JSON.
"""

    try:
        log.info(f"Triaging ticket {ticket_id}: {subject[:50]}...")

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system",  "content": SYSTEM_PROMPT},
                {"role": "user",    "content": user_message}
            ],
            temperature=0.2,   # low temp = consistent, predictable output
            max_tokens=800,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if model wraps in ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(raw)
        result["ticket_id"] = ticket_id
        result["status"] = "success"

        log.info(f"Ticket {ticket_id} → {result['priority']} / {result['department']}")
        return result

    except json.JSONDecodeError as e:
        log.error(f"JSON parse failed for ticket {ticket_id}: {e}")
        return {"ticket_id": ticket_id, "status": "error", "error": str(e)}

    except Exception as e:
        log.error(f"Triage failed for ticket {ticket_id}: {e}")
        return {"ticket_id": ticket_id, "status": "error", "error": str(e)}
