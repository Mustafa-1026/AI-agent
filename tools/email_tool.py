"""
email_sender.py
================

Email composition and sending tool for the AI-powered Faculty
Intelligence & Research Discovery System.

Single Responsibility
----------------------
This module is responsible ONLY for:
    - Composing a formatted email (subject + body) from given content
    - Sending that email via SMTP — but ONLY when explicitly confirmed

This module explicitly does NOT:
    - Decide what an email should say (that's student_agent.py /
      professor_agent.py's generate_email_draft() logic)
    - Perform retrieval, ranking, or any RAG/agent reasoning
    - Send anything without an explicit, caller-provided confirmation

Human-in-the-loop safety design
--------------------------------
`send_email()` requires `confirm=True` to actually dispatch mail. This
is a deliberate design choice, not an oversight: no faculty member
should ever be emailed as a side effect of testing, debugging, or an
agent's automatic reasoning. The calling agent is responsible for
surfacing the composed draft to the human user and only invoking
`send_email(..., confirm=True)` after the user has explicitly approved
it — mirroring the "confirmation before logging" step in this
project's overall flow.

Configuration
--------------
Reads the following from a `.env` file (via python-dotenv), matching
the existing pattern used in tools/tavily_search.py:

    EMAIL_ADDRESS   - the sender's email address
    EMAIL_PASSWORD  - the sender's app password / SMTP password
    SMTP_SERVER     - SMTP host (defaults to "smtp.gmail.com")
    SMTP_PORT       - SMTP port (defaults to 587, STARTTLS)

Author: AI Agent Hackathon Team
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS: Optional[str] = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))

#: Valid values for the `relationship` parameter of compose_email().
VALID_RELATIONSHIPS = {"student_to_professor", "professor_to_professor"}


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

def _default_subject(relationship: str, shared_topic: str = "") -> str:
    """
    Build a sensible default subject line for a given relationship
    type when the caller doesn't supply one.

    Args:
        relationship: "student_to_professor" or "professor_to_professor".
        shared_topic: Optional research area/topic to fold into the
            subject for specificity.

    Returns:
        A default subject line string.
    """
    if relationship == "professor_to_professor":
        return (
            f"Potential Research Collaboration in {shared_topic}"
            if shared_topic
            else "Potential Research Collaboration Opportunity"
        )
    return (
        f"Request for Research Guidance in {shared_topic}"
        if shared_topic
        else "Request for Research Guidance"
    )


def _default_body(
    relationship: str,
    recipient_name: str,
    sender_name: str,
    context_line: str,
) -> str:
    """
    Build a sensible default body for a given relationship type when
    the caller doesn't supply full custom body text.

    Args:
        relationship: "student_to_professor" or "professor_to_professor".
        recipient_name: Name of the person being emailed.
        sender_name: Name to sign the email off with.
        context_line: A grounded sentence explaining the relevance
            (e.g. shared research areas, matched skills) — supplied by
            the calling agent from retrieved/derived data, never
            invented here.

    Returns:
        A formatted email body string.
    """
    signature = sender_name.strip() if sender_name and sender_name.strip() else "[Your Name]"

    if relationship == "professor_to_professor":
        return (
            f"Dear Dr. {recipient_name},\n\n"
            f"I hope this email finds you well. I am reaching out "
            f"regarding a potential research collaboration.\n\n"
            f"{context_line}\n\n"
            f"I would welcome the opportunity to discuss this further "
            f"and explore how our work might complement one another.\n\n"
            f"Best regards,\n{signature}"
        )

    # student_to_professor (default)
    return (
        f"Dear {recipient_name},\n\n"
        f"I hope this email finds you well. I am a student interested "
        f"in your research and would greatly value your guidance.\n\n"
        f"{context_line}\n\n"
        f"I would be grateful for the opportunity to discuss this "
        f"further, whether through a short meeting or over email, at "
        f"your convenience.\n\n"
        f"Thank you very much for your time and consideration.\n\n"
        f"Best regards,\n{signature}"
    )


def compose_email(
    recipient_email: str,
    recipient_name: str = "",
    subject: str = "",
    body: str = "",
    sender_name: str = "",
    relationship: str = "student_to_professor",
    context_line: str = "",
    shared_topic: str = "",
) -> Dict[str, str]:
    """
    Compose a structured email payload without sending anything.

    Supports two tone/template variants via `relationship`:
        - "student_to_professor": deferential, mentorship-request tone.
        - "professor_to_professor": peer tone, collaboration-proposal
          framing (pairs naturally with collaboration_engine.py's
          shared-research-area output).

    If `body` is not supplied, a default template for the given
    `relationship` is generated using `recipient_name`, `sender_name`,
    and `context_line` (a grounded, agent-supplied sentence — this
    function never invents relevance text on its own).

    Args:
        recipient_email: The recipient's email address.
        recipient_name: The recipient's display name, used in the
            greeting line of the default template.
        subject: Optional custom subject line. If omitted, a default
            is generated based on `relationship` and `shared_topic`.
        body: Optional custom email body. If omitted, a default
            template is generated based on `relationship`.
        sender_name: Optional display name to sign off with.
        relationship: Either "student_to_professor" (default) or
            "professor_to_professor". Falls back to
            "student_to_professor" if an unrecognized value is passed.
        context_line: A grounded sentence explaining why this contact
            is relevant (e.g. "Your work in Federated Learning aligns
            with my research interests."). Only used when `body` is
            not supplied.
        shared_topic: Optional topic/research area used to make the
            default subject line more specific.

    Returns:
        A dictionary representing the composed (but unsent) email:
            {
                "to": str,
                "subject": str,
                "body": str,
                "relationship": str,
                "status": "drafted"
            }
        This dictionary is safe to display to the user for review
        before calling send_email().
    """
    clean_recipient = (recipient_email or "").strip()
    clean_relationship = (
        relationship if relationship in VALID_RELATIONSHIPS else "student_to_professor"
    )

    clean_subject = (subject or "").strip() or _default_subject(
        clean_relationship, shared_topic.strip() if shared_topic else ""
    )

    if body and body.strip():
        clean_body = body.strip()
        if sender_name and sender_name.strip() not in clean_body:
            clean_body = f"{clean_body}\n\n{sender_name.strip()}"
    else:
        clean_body = _default_body(
            relationship=clean_relationship,
            recipient_name=(recipient_name or "").strip() or "Colleague",
            sender_name=sender_name,
            context_line=(context_line or "").strip()
            or "I believe there is meaningful alignment worth exploring further.",
        )

    return {
        "to": clean_recipient,
        "subject": clean_subject,
        "body": clean_body,
        "relationship": clean_relationship,
        "status": "drafted",
    }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_email_address(address: str) -> bool:
    """
    Perform a lightweight sanity check on an email address's shape.

    This is intentionally simple (not full RFC 5322 validation) since
    its only purpose is to catch obviously malformed input before
    attempting an SMTP send.

    Args:
        address: The email address to check.

    Returns:
        True if the address has a plausible "local@domain.tld" shape.
    """
    if not address or "@" not in address:
        return False
    local_part, _, domain_part = address.partition("@")
    return bool(local_part) and "." in domain_part and not domain_part.startswith(".")


def _credentials_available() -> bool:
    """
    Check whether sender credentials are configured.

    Returns:
        True if both EMAIL_ADDRESS and EMAIL_PASSWORD are set.
    """
    return bool(EMAIL_ADDRESS) and bool(EMAIL_PASSWORD)


# ---------------------------------------------------------------------------
# Sending (confirmation-gated)
# ---------------------------------------------------------------------------

def send_email(
    recipient_email: str,
    subject: str,
    body: str,
    confirm: bool = False,
) -> Dict[str, str]:
    """
    Send an email via SMTP — but ONLY if `confirm=True` is explicitly
    passed by the caller. This is a hard safety gate: no email is ever
    sent as an automatic side effect of agent reasoning or testing.

    Args:
        recipient_email: The recipient's email address.
        subject: The email subject line.
        body: The full email body text.
        confirm: Must be explicitly set to True by the caller (after
            the human user has reviewed and approved the draft) for
            the email to actually be sent. Defaults to False.

    Returns:
        A dictionary describing the outcome:
            {"status": "not_confirmed", "message": "..."}          if confirm=False
            {"status": "invalid_recipient", "message": "..."}      if the address looks malformed
            {"status": "missing_credentials", "message": "..."}    if .env is not configured
            {"status": "sent", "message": "..."}                   on success
            {"status": "failed", "message": "..."}                 on any SMTP/connection error
        This function never raises — all failure modes are returned
        as a structured result so the calling agent can react
        gracefully.
    """
    if not confirm:
        return {
            "status": "not_confirmed",
            "message": (
                "Email not sent: this action requires explicit user "
                "confirmation before any message is dispatched."
            ),
        }

    clean_recipient = (recipient_email or "").strip()
    if not _validate_email_address(clean_recipient):
        return {
            "status": "invalid_recipient",
            "message": f"'{recipient_email}' does not look like a valid email address.",
        }

    if not _credentials_available():
        return {
            "status": "missing_credentials",
            "message": (
                "Email not sent: EMAIL_ADDRESS and/or EMAIL_PASSWORD are "
                "not configured. Please check your .env file."
            ),
        }

    message = EmailMessage()
    message["From"] = EMAIL_ADDRESS
    message["To"] = clean_recipient
    message["Subject"] = (subject or "").strip() or "Faculty Outreach"
    message.set_content((body or "").strip())

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls(context=context)
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError:
        return {
            "status": "failed",
            "message": (
                "SMTP authentication failed. Check EMAIL_ADDRESS/"
                "EMAIL_PASSWORD (Gmail requires an App Password, not "
                "your regular account password)."
            ),
        }
    except (smtplib.SMTPException, TimeoutError, OSError) as exc:
        return {
            "status": "failed",
            "message": f"Failed to send email: {exc}.",
        }
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        return {
            "status": "failed",
            "message": f"Unexpected error while sending email: {exc}.",
        }

    return {
        "status": "sent",
        "message": f"Email successfully sent to {clean_recipient}.",
    }


# ---------------------------------------------------------------------------
# Manual/standalone execution (useful for quick sanity checks during dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    student_draft = compose_email(
        recipient_email="professor@example.edu",
        recipient_name="Dr. Rao",
        sender_name="Aarav Mehta",
        relationship="student_to_professor",
        context_line="Your work in Federated Learning closely aligns with my research interests.",
        shared_topic="Federated Learning",
    )
    print("Student-to-professor draft:", student_draft)

    professor_draft = compose_email(
        recipient_email="colleague@example.edu",
        recipient_name="Sharma",
        sender_name="Dr. Rao",
        relationship="professor_to_professor",
        context_line="We both list Explainable AI as a shared research area, and I believe our approaches could complement each other well.",
        shared_topic="Explainable AI",
    )
    print("Professor-to-professor draft:", professor_draft)

    draft = student_draft

    # NOTE: confirm=False by default — this will NOT actually send.
    result = send_email(
        recipient_email=draft["to"],
        subject=draft["subject"],
        body=draft["body"],
        confirm=False,
    )
    print("Send result (unconfirmed):", result)
