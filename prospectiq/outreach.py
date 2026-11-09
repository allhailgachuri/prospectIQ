"""
Personalised outreach package generation for ProspectIQ.

Generates for each qualified prospect:
  A. WhatsApp / SMS message
  B. Email (subject + body)
  C. Phone call script (full + short version)
  D. Follow-up strategy

Every message includes https://builtbyrushion.vercel.app/

IMPORTANT: This module prepares outreach for human review.
           Nothing is sent automatically.
"""
from typing import Any

from .config import AGENCY_NAME, AGENCY_URL, AGENCY_PORTFOLIO
from .logger import get_logger

log = get_logger(__name__)

FOUNDER_NAME = "Rushion"


def _business_intro(business: dict[str, Any], intelligence: dict[str, Any]) -> str:
    """One specific, evidence-based observation about the business."""
    name     = business.get("name", "your business")
    nb       = business.get("neighbourhood") or "Nairobi"
    ws       = business.get("website_status") or business.get("website_presence", "")
    industry = intelligence.get("industry", "")

    if ws in ("WEBSITE_NOT_FOUND_AFTER_CHECKS", "not_listed_in_osm"):
        return (
            f"I came across {name} in {nb} while researching {industry.split('—')[0].strip()} "
            f"businesses in Nairobi, and I noticed the business doesn't appear to have an "
            f"official website yet."
        )
    elif ws == "WEBSITE_UNREACHABLE":
        url = business.get("website", "your website")
        return (
            f"I came across {name} in {nb} and noticed that the website ({url}) "
            f"appears to be currently unavailable."
        )
    elif ws == "VERIFIED_WEBSITE":
        ql = business.get("audit_quality_label", "")
        url = business.get("verified_url") or business.get("website", "")
        if ql in ("POOR", "WEAK"):
            return (
                f"I came across {name} in {nb} and had a look at the website. "
                f"I noticed a few things that could be improved — including mobile experience "
                f"and how easy it is for customers to get in touch."
            )
        else:
            return (
                f"I came across {name} in {nb} while researching {industry.split('—')[0].strip()} "
                f"businesses in Nairobi."
            )
    return (
        f"I came across {name} in {nb} while researching businesses in Nairobi."
    )


def generate_whatsapp(business: dict[str, Any], intelligence: dict[str, Any]) -> str:
    """Generate a WhatsApp / SMS outreach message."""
    name     = business.get("name", "your business")
    whatsapp = business.get("whatsapp")
    phone    = business.get("phone")
    primary  = intelligence.get("primary_service", "website development")
    intro    = _business_intro(business, intelligence)

    if not whatsapp and not phone:
        return (
            "WhatsApp outreach unavailable — no public WhatsApp number or phone number "
            "was found for this business in verified sources."
        )

    contact_note = ""
    if whatsapp:
        contact_note = f"(WhatsApp contact sourced from OpenStreetMap: {whatsapp})"
    elif phone:
        contact_note = (
            f"(Note: Only a general phone number was found: {phone}. "
            "Verify whether this number accepts WhatsApp messages before sending.)"
        )

    message = f"""Hi, I'm {FOUNDER_NAME} from {AGENCY_NAME} 👋

{intro}

I specialise in {primary.lower()} for businesses in Nairobi, and I think there's a real opportunity here to help {name} attract more customers online.

I'd love to have a quick 10-minute call to understand your goals and share a few ideas — no commitment required.

You can see our work here: {AGENCY_URL}

Would that work for you?

— {FOUNDER_NAME}, {AGENCY_NAME}

{contact_note}"""
    return message.strip()


def generate_email(business: dict[str, Any], intelligence: dict[str, Any]) -> dict[str, str]:
    """Generate a personalised email (subject + body)."""
    name     = business.get("name", "your business")
    email    = business.get("email")
    primary  = intelligence.get("primary_service", "website development")
    services = intelligence.get("services", [])
    opp      = intelligence.get("opportunity", "")
    nb       = business.get("neighbourhood") or "Nairobi"
    intro    = _business_intro(business, intelligence)

    if not email:
        return {
            "subject": "",
            "body":    (
                "Email outreach unavailable — no public business email address was found "
                "for this business in verified sources."
            ),
            "available": "false",
        }

    # Subject line
    ws = business.get("website_status") or business.get("website_presence", "")
    if ws in ("WEBSITE_NOT_FOUND_AFTER_CHECKS", "not_listed_in_osm"):
        subject = f"Helping {name} build a professional online presence"
    elif ws == "WEBSITE_UNREACHABLE":
        subject = f"Quick note about {name}'s website"
    else:
        subject = f"A digital opportunity for {name} in {nb}"

    # Additional services mention
    extra_services = [s for s in services if s != primary][:2]
    extra_line = ""
    if extra_services:
        extra_line = (
            f"\n\nBeyond that, depending on what matters most to your business, "
            f"we could also help with: {', '.join(extra_services).lower()}."
        )

    body = f"""Dear {name} Team,

{intro}

{opp}

My name is {FOUNDER_NAME}, and I run {AGENCY_NAME} — a technology agency based in Nairobi that helps local businesses build professional digital tools. Our work spans website development, e-commerce, custom software, business analytics and automation.

For {name}, I believe the most valuable place to start would be: {primary}.{extra_line}

This isn't a generic pitch — I specifically chose to reach out because I think there's a meaningful opportunity here. I'd be glad to have a 20-minute call to understand your business better and share some concrete ideas, completely free of charge.

You can view our portfolio and previous work here:
{AGENCY_URL}

Would you be open to a brief call this week or next? You can reply to this email or reach me directly.

Warm regards,

{FOUNDER_NAME}
Founder, {AGENCY_NAME}
{AGENCY_URL}

---
{AGENCY_NAME} | Nairobi, Kenya | {AGENCY_URL}
This message was sent to a publicly listed business email address for professional enquiry purposes."""

    return {
        "subject":   subject,
        "body":      body.strip(),
        "to":        email,
        "available": "true",
    }


def generate_call_script(business: dict[str, Any], intelligence: dict[str, Any]) -> dict[str, str]:
    """Generate a phone call script (full + short version + objection handling)."""
    name    = business.get("name", "the business")
    phone   = business.get("phone") or business.get("whatsapp")
    primary = intelligence.get("primary_service", "website development")
    opp     = intelligence.get("opportunity", "")
    nb      = business.get("neighbourhood") or "Nairobi"

    phone_note = f"Phone: {phone}" if phone else "No verified phone found — verify before calling."

    full_script = f"""PHONE CALL SCRIPT — {name.upper()}
{phone_note}

────────────────────────────────────────
FULL SCRIPT
────────────────────────────────────────

OPENING
-------
"Hello, good [morning/afternoon]. Is this {name}?"
[Wait for confirmation]
"Wonderful. My name is {FOUNDER_NAME}, and I'm calling from {AGENCY_NAME}, a technology agency here in Nairobi. Could I speak with the person who handles your business's marketing or digital presence? It will only take a minute."

[If transferred or speaking with right person]

INTRODUCTION
------------
"Thank you for your time. I'll be brief — I was researching {intelligence.get('industry', 'businesses')} businesses in {nb}, and I came across {name}. {opp.split('.')[0] if opp else 'I had a look at your online presence and noticed a few things that could be working harder for you.'}"

SPECIFIC OBSERVATION
--------------------
"{_business_intro(business, intelligence).replace('I came across ', 'I noticed that ')}"

VALUE PROPOSITION
-----------------
"At {AGENCY_NAME}, we specialise in {primary.lower()} for businesses exactly like yours. We've helped businesses in Nairobi establish a strong online presence that actually brings in new customers."

DISCOVERY QUESTION
------------------
"I'm curious — do you currently have a system for how customers find you or get in touch online? Or is most of your business coming through word of mouth and walk-ins?"
[Listen carefully — this shapes the conversation]

SUGGESTED NEXT STEP
--------------------
"I'd love to put together a few specific ideas for {name} and share them in a short 20-minute call or meeting — no cost, no obligation. It's just a conversation. Would that be something you'd be open to?"

PROFESSIONAL CLOSE
------------------
"Wonderful. Can I send you our portfolio in the meantime? Our website is {AGENCY_URL} — you can see the kind of work we do there. I'll follow up [tomorrow / later this week] to confirm a time. Thank you so much for your time, [name if known]. Have a great day."

────────────────────────────────────────
COMMON OBJECTIONS
────────────────────────────────────────

"We already have a website."
→ "That's great — I actually saw it. I noticed [specific audit finding]. Would you be interested in a quick review of what could be improved? It's free and takes 10 minutes."

"We're not interested."
→ "That's completely fine — I appreciate you saying so directly. I'll leave our details in case anything changes: {AGENCY_URL}. Have a great day."

"We don't have budget for this."
→ "Absolutely understood. What I'd suggest is just a free conversation to understand your goals — there's no commitment. When budgets do open up, you'll know exactly what's available and what it costs."

"Who are you again?"
→ "My name is {FOUNDER_NAME}, from {AGENCY_NAME} — a Nairobi-based technology agency. Our website is {AGENCY_URL}. Would you like me to send you our portfolio?"

"Call back another time."
→ "Of course — when would be a better time? I want to make sure I'm not interrupting." [Note the agreed time and follow up once only.]

────────────────────────────────────────
RESPECTFUL CLOSE IF NOT INTERESTED
────────────────────────────────────────
"I completely understand. I won't take up any more of your time. If you ever need digital support in the future, please don't hesitate to reach out — our website is {AGENCY_URL}. Thanks so much and have a great day."
"""

    short_script = f"""SHORT VERSION (if the person is busy)
--------------------------------------
"Hi, this is {FOUNDER_NAME} from {AGENCY_NAME} in Nairobi. I'm reaching out because I noticed {name} might benefit from [website development / improved digital presence]. Could I send you a quick note with some ideas, or is there a better time to talk? Our website is {AGENCY_URL}."
"""

    return {
        "full_script":  full_script.strip(),
        "short_script": short_script.strip(),
        "phone":        phone or "Not available",
    }


def generate_followup_strategy(business: dict[str, Any], intelligence: dict[str, Any]) -> str:
    """Recommend a non-intrusive follow-up sequence."""
    name = business.get("name", "this business")
    priority = intelligence.get("priority", "MEDIUM")

    if priority == "HIGH":
        return f"""FOLLOW-UP STRATEGY — {name} (HIGH PRIORITY)

Day 1     : Send initial outreach (WhatsApp or email, depending on available contact).
Day 3-4   : If no response, one polite follow-up: "Just checking in — did my message reach you?"
Day 10    : If still no response, one final brief message referencing a specific detail about the business.
After that: Do not contact again unless the business reaches out first.

If you receive a clear "not interested": remove from active outreach immediately.
Mark the prospect as DNC (Do Not Contact) in the system.

Note: All outreach must be reviewed by a human before sending.
      Never send automated bulk messages.
"""
    elif priority == "MEDIUM":
        return f"""FOLLOW-UP STRATEGY — {name} (MEDIUM PRIORITY)

Day 1     : Send initial outreach.
Day 7     : One follow-up if no response.
After that: Do not contact again. Move to 'low priority' pool.

If the business responds positively: schedule a discovery call within 48 hours.
If not interested: mark DNC immediately.
"""
    else:
        return f"""FOLLOW-UP STRATEGY — {name} (LOW PRIORITY)

Day 1     : Send one initial message only.
No follow-up unless the business responds.

This is a lower-priority prospect — focus outreach effort on HIGH and MEDIUM prospects first.
"""


def build_outreach_package(
    business: dict[str, Any],
    intelligence: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the complete outreach package for one prospect.
    Returns a dict with all outreach components.
    """
    return {
        "whatsapp_message":    generate_whatsapp(business, intelligence),
        "email":               generate_email(business, intelligence),
        "call_script":         generate_call_script(business, intelligence),
        "followup_strategy":   generate_followup_strategy(business, intelligence),
        "agency_url":          AGENCY_URL,
    }
