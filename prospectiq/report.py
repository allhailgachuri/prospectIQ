"""
Professional Word (.docx) report generator for ProspectIQ.

Generates a fully structured prospect intelligence report using python-docx.
Only real, verified data from the database is included.
If no qualified prospects exist, a 'no results' report is produced.

Report structure:
  - Cover page
  - Research disclaimer
  - Table of contents (manual)
  - Executive summary
  - Market overview
  - Prioritised prospect directory (one section per business)
  - Action plan
  - Source references
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from .config import AGENCY_NAME, AGENCY_URL, AGENCY_PORTFOLIO
from .logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Branding colours (BuiltByRushion palette)
# ---------------------------------------------------------------------------
BRAND_BLUE   = RGBColor(0x00, 0x4E, 0xCC)   # #004ECC
BRAND_DARK   = RGBColor(0x0F, 0x17, 0x2A)   # #0F172A
BRAND_ACCENT = RGBColor(0x06, 0xB6, 0xD4)   # #06B6D4 (cyan accent)
GREY_TEXT    = RGBColor(0x64, 0x74, 0x8B)   # #64748B


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_hyperlink(paragraph, text: str, url: str):
    """Add a clickable hyperlink to a paragraph."""
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rStyle = OxmlElement("w:rStyle")
    rStyle.set(qn("w:val"), "Hyperlink")
    rPr.append(rStyle)
    new_run.append(rPr)
    new_run_text = OxmlElement("w:t")
    new_run_text.text = text
    new_run.append(new_run_text)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def _set_cell_bg(cell, hex_color: str):
    """Set table cell background colour."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def _heading(doc: Document, text: str, level: int = 1, color: RGBColor = BRAND_DARK):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = color
    return p


def _bold_label(para, label: str, value: str, label_color: RGBColor = BRAND_BLUE):
    run = para.add_run(f"{label}: ")
    run.bold = True
    run.font.color.rgb = label_color
    para.add_run(value or "Not available")


def _add_info_table(doc: Document, rows: list[tuple[str, str]]):
    """Add a two-column info table (label | value)."""
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for i, (label, value) in enumerate(rows):
        label_cell = table.cell(i, 0)
        value_cell = table.cell(i, 1)
        label_cell.width = Inches(1.8)
        value_cell.width = Inches(4.5)
        _set_cell_bg(label_cell, "EFF6FF")
        lp = label_cell.paragraphs[0]
        lr = lp.add_run(label)
        lr.bold = True
        lr.font.color.rgb = BRAND_DARK
        vp = value_cell.paragraphs[0]
        vp.add_run(value or "—")
    doc.add_paragraph()


def _page_break(doc: Document):
    doc.add_page_break()


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def _cover_page(doc: Document, date_str: str, prospect_count: int):
    doc.add_paragraph()
    doc.add_paragraph()

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run("ProspectIQ")
    title_run.font.size = Pt(36)
    title_run.bold = True
    title_run.font.color.rgb = BRAND_BLUE

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub_p.add_run("Nairobi Business Prospect Intelligence Report")
    sub_run.font.size = Pt(20)
    sub_run.font.color.rgb = BRAND_DARK

    doc.add_paragraph()

    for label, value in [
        ("Coverage",       "Nairobi County, Kenya"),
        ("Prepared for",   f"{AGENCY_NAME} — {AGENCY_URL}"),
        ("Report date",    date_str),
        ("Qualified prospects", str(prospect_count)),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p.add_run(f"{label}: ")
        r1.bold = True
        r1.font.color.rgb = BRAND_BLUE
        r2 = p.add_run(value)
        r2.font.color.rgb = BRAND_DARK

    doc.add_paragraph()
    disc_p = doc.add_paragraph()
    disc_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    disc_run = disc_p.add_run(
        "RESEARCH DISCLAIMER: This report contains real businesses discovered from "
        "OpenStreetMap (ODbL licence) and publicly accessible sources. Website audit "
        "results are based on automated checks of publicly accessible web pages. "
        "All data should be verified by a human before acting on it. "
        "No outreach has been sent. Contact details are sourced from publicly published "
        "business information only."
    )
    disc_run.font.size = Pt(9)
    disc_run.italic = True
    disc_run.font.color.rgb = GREY_TEXT

    _page_break(doc)


def _executive_summary(doc: Document, stats: dict[str, Any]):
    _heading(doc, "Executive Summary", level=1)

    summary_rows = [
        ("Businesses discovered",          str(stats.get("total_discovered", 0))),
        ("Unique businesses (after dedup)", str(stats.get("total_unique", 0))),
        ("With verified websites",          str(stats.get("verified_websites", 0))),
        ("Website not found after checks",  str(stats.get("no_website", 0))),
        ("Website unreachable",             str(stats.get("unreachable", 0))),
        ("With weak website (score < 60)",  str(stats.get("weak_website", 0))),
        ("With verified public email",      str(stats.get("with_email", 0))),
        ("With verified public phone",      str(stats.get("with_phone", 0))),
        ("Qualified prospects",             str(stats.get("qualified", 0))),
        ("High priority prospects",         str(stats.get("high_priority", 0))),
        ("Medium priority prospects",       str(stats.get("medium_priority", 0))),
        ("Requiring manual review",         str(stats.get("needs_review", 0))),
    ]
    _add_info_table(doc, summary_rows)

    doc.add_paragraph(
        "Coverage note: Discovery used the OpenStreetMap Overpass API covering the "
        "Nairobi County approximate envelope. OSM data represents community-contributed "
        "information and may not include all businesses. Website status was checked "
        "programmatically; results reflect the state of websites at the time of checking. "
        "Data is licensed under ODbL — see https://www.openstreetmap.org/copyright."
    ).italic = True

    _page_break(doc)


def _market_overview(doc: Document, stats: dict[str, Any]):
    _heading(doc, "Market Overview", level=1)

    if stats.get("by_category"):
        _heading(doc, "Businesses by Category", level=2)
        tbl = doc.add_table(rows=1 + len(stats["by_category"]), cols=2)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        hdr[0].text = "Category"
        hdr[1].text = "Count"
        _set_cell_bg(hdr[0], "004ECC")
        _set_cell_bg(hdr[1], "004ECC")
        for cell in hdr:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.bold = True
        for i, row in enumerate(stats["by_category"]):
            r = tbl.rows[i + 1].cells
            r[0].text = row.get("category") or "(none)"
            r[1].text = str(row.get("n", 0))
        doc.add_paragraph()

    if stats.get("by_neighbourhood"):
        _heading(doc, "Businesses by Neighbourhood (Top 20)", level=2)
        tbl = doc.add_table(rows=1 + len(stats["by_neighbourhood"]), cols=2)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        hdr[0].text = "Neighbourhood"
        hdr[1].text = "Count"
        _set_cell_bg(hdr[0], "004ECC")
        _set_cell_bg(hdr[1], "004ECC")
        for cell in hdr:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.bold = True
        for i, row in enumerate(stats["by_neighbourhood"]):
            r = tbl.rows[i + 1].cells
            r[0].text = row.get("neighbourhood") or "(unknown)"
            r[1].text = str(row.get("n", 0))
        doc.add_paragraph()

    _page_break(doc)


def _prospect_section(doc: Document, prospect: dict[str, Any], index: int):
    """Write a complete prospect profile section."""
    biz      = prospect["business"]
    intel    = prospect["intelligence"]
    outreach = prospect["outreach"]

    name   = biz.get("name", "Unknown Business")
    nb     = biz.get("neighbourhood") or "Nairobi"
    score  = intel.get("lead_score", 0)
    priority = intel.get("priority", "UNKNOWN")

    # Section heading
    _heading(doc, f"{index}. {name}", level=1, color=BRAND_BLUE)

    # Priority badge
    priority_colors = {
        "HIGH":               "DC2626",
        "MEDIUM":             "D97706",
        "LOW":                "6B7280",
        "NEEDS_MANUAL_REVIEW":"7C3AED",
    }
    badge_p = doc.add_paragraph()
    badge_run = badge_p.add_run(f"  {priority} PRIORITY  |  Lead Score: {score}/100  ")
    badge_run.bold = True
    badge_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # ── 1. Business identity ──
    _heading(doc, "1. Business Identity", level=2)
    rows = [
        ("Business name",   name),
        ("Industry",        intel.get("industry", "—")),
        ("What it does",    intel.get("what_it_does", "—")),
        ("Neighbourhood",   nb),
        ("Address",         biz.get("address") or "Not available"),
        ("Coordinates",     f"{biz.get('latitude')}, {biz.get('longitude')}" if biz.get("latitude") else "Not available"),
        ("Map link",        biz.get("map_link") or "Not available"),
        ("OSM category",    f"{biz.get('category')} / {biz.get('subcategory')}" if biz.get("subcategory") else biz.get("category") or "—"),
        ("Opening hours",   biz.get("opening_hours") or "Not available"),
    ]
    _add_info_table(doc, rows)

    if biz.get("map_link"):
        p = doc.add_paragraph()
        p.add_run("Map: ")
        _add_hyperlink(p, biz["map_link"], biz["map_link"])
        doc.add_paragraph()

    # ── 2. How ProspectIQ found this business ──
    _heading(doc, "2. How ProspectIQ Found This Business", level=2)
    _add_info_table(doc, [
        ("Source",           biz.get("source", "OpenStreetMap")),
        ("Source record ID", biz.get("source_record_id", "—")),
        ("First discovered", biz.get("first_seen_at", "—")),
        ("Last verified",    biz.get("last_seen_at", "—")),
        ("Confidence",       "OSM community-verified location data"),
    ])

    # ── 3. Digital presence ──
    _heading(doc, "3. Current Digital Presence", level=2)
    ws = biz.get("website_status") or biz.get("website_presence", "Unknown")
    audit_label = biz.get("audit_quality_label") or "Not audited"
    website_rows = [
        ("Website (OSM)",      biz.get("website") or "Not listed in OSM"),
        ("Verified URL",       biz.get("verified_url") or "—"),
        ("Website status",     ws),
        ("HTTPS",              str(biz.get("https")) if biz.get("https") is not None else "—"),
        ("Audit score",        f"{biz.get('audit_score')}/100" if biz.get("audit_score") is not None else "Not audited"),
        ("Quality label",      audit_label),
        ("Mobile friendly",    str(biz.get("audit_mobile_friendly")) if biz.get("audit_mobile_friendly") is not None else "—"),
        ("Contact on site",    str(biz.get("audit_has_contact")) if biz.get("audit_has_contact") is not None else "—"),
        ("Facebook",           biz.get("facebook") or "—"),
        ("Instagram",          biz.get("instagram") or "—"),
    ]
    _add_info_table(doc, website_rows)

    # Audit findings
    if biz.get("audit_findings_json"):
        try:
            findings = json.loads(biz["audit_findings_json"])
            if findings:
                _heading(doc, "Website Audit Findings", level=3)
                tbl = doc.add_table(rows=1 + len(findings), cols=3)
                tbl.style = "Table Grid"
                hdr = tbl.rows[0].cells
                for j, h in enumerate(["Check", "Result", "Detail"]):
                    hdr[j].text = h
                    _set_cell_bg(hdr[j], "EFF6FF")
                    for para in hdr[j].paragraphs:
                        for run in para.runs:
                            run.bold = True
                for i, f in enumerate(findings):
                    r = tbl.rows[i + 1].cells
                    r[0].text = f.get("check", "")
                    r[1].text = f.get("result", "")
                    r[2].text = f.get("detail", "")
                    if f.get("result") == "FAIL":
                        _set_cell_bg(r[1], "FEE2E2")
                    elif f.get("result") == "WEAK":
                        _set_cell_bg(r[1], "FEF3C7")
                    elif f.get("result") == "PASS":
                        _set_cell_bg(r[1], "DCFCE7")
                doc.add_paragraph()
        except Exception:
            pass

    # ── 4. Contact information ──
    _heading(doc, "4. Contact Information", level=2)
    _add_info_table(doc, [
        ("Phone",     biz.get("phone") or "Not found in public sources"),
        ("Email",     biz.get("email") or "Not found in public sources"),
        ("WhatsApp",  biz.get("whatsapp") or "Not explicitly published"),
        ("Website",   biz.get("verified_url") or biz.get("website") or "—"),
    ])
    doc.add_paragraph(
        "Contact details sourced from OpenStreetMap public tags only. "
        "Verify before outreach. Do not use personal contact information."
    ).italic = True

    # ── 5. Why this business may need BuiltByRushion ──
    _heading(doc, f"5. Why {name} May Benefit from {AGENCY_NAME}", level=2)
    doc.add_paragraph(intel.get("opportunity", ""))
    doc.add_paragraph()
    reasons_p = doc.add_paragraph()
    reasons_p.add_run("Score rationale:").bold = True
    for r in intel.get("score_reasons", []):
        doc.add_paragraph(f"• {r}", style="List Bullet")

    # ── 6. Recommended services ──
    _heading(doc, "6. Recommended Services", level=2)
    p = doc.add_paragraph()
    p.add_run("Primary service: ").bold = True
    p.add_run(intel.get("primary_service", "—"))
    services = intel.get("services", [])
    if len(services) > 1:
        p2 = doc.add_paragraph()
        p2.add_run("Additional services to consider: ").bold = True
        p2.add_run(", ".join(s for s in services if s != intel.get("primary_service")))
    doc.add_paragraph()
    doc.add_paragraph(
        "Note: These recommendations are based on observed data. Verify assumptions "
        "in a discovery call before proposing a specific solution or price."
    ).italic = True

    # ── 7. Personalised outreach ──
    _heading(doc, "7. Personalised Outreach Package", level=2)

    # WhatsApp
    _heading(doc, "WhatsApp / SMS Message", level=3)
    wa = outreach.get("whatsapp_message", "")
    doc.add_paragraph(wa)

    # Email
    _heading(doc, "Email Outreach", level=3)
    email_data = outreach.get("email", {})
    if isinstance(email_data, dict):
        if email_data.get("available") == "true":
            subj_p = doc.add_paragraph()
            subj_p.add_run("Subject: ").bold = True
            subj_p.add_run(email_data.get("subject", ""))
            doc.add_paragraph()
            doc.add_paragraph(email_data.get("body", ""))
        else:
            doc.add_paragraph(email_data.get("body", "No email available."))

    # Call script
    _heading(doc, "Phone Call Script", level=3)
    call_data = outreach.get("call_script", {})
    if isinstance(call_data, dict):
        doc.add_paragraph(call_data.get("full_script", ""))
        doc.add_paragraph()
        doc.add_paragraph(call_data.get("short_script", ""))

    # Follow-up
    _heading(doc, "Follow-Up Strategy", level=3)
    doc.add_paragraph(outreach.get("followup_strategy", ""))

    # ── 8. Qualification summary ──
    _heading(doc, "8. Prospect Qualification Summary", level=2)
    _add_info_table(doc, [
        ("Lead score",        f"{intel.get('lead_score', 0)}/100"),
        ("Priority tier",     intel.get("priority", "—")),
        ("Likely customers",  intel.get("likely_customers", "—")),
        ("Evidence strength", "OSM location + business data"),
        ("Human verification needed", "Yes — verify contacts, confirm business is active, confirm address before outreach"),
    ])

    if intel.get("score_deductions"):
        doc.add_paragraph()
        doc.add_paragraph("Limitations and caveats:").bold = True
        for d in intel["score_deductions"]:
            doc.add_paragraph(f"• {d}", style="List Bullet")

    _page_break(doc)


def _action_plan(doc: Document, prospects: list[dict[str, Any]]):
    _heading(doc, "Action Plan", level=1)

    high    = [p for p in prospects if p["intelligence"].get("priority") == "HIGH"]
    medium  = [p for p in prospects if p["intelligence"].get("priority") == "MEDIUM"]
    review  = [p for p in prospects if p["intelligence"].get("priority") == "NEEDS_MANUAL_REVIEW"]

    _heading(doc, "Top Prospects to Contact First (HIGH PRIORITY)", level=2)
    if high:
        tbl = doc.add_table(rows=1 + len(high), cols=4)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        for j, h in enumerate(["#", "Business", "Neighbourhood", "Primary Service"]):
            hdr[j].text = h
            _set_cell_bg(hdr[j], "004ECC")
            for para in hdr[j].paragraphs:
                for run in para.runs:
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.bold = True
        for i, p in enumerate(high):
            biz   = p["business"]
            intel = p["intelligence"]
            r = tbl.rows[i + 1].cells
            r[0].text = str(i + 1)
            r[1].text = biz.get("name", "—")
            r[2].text = biz.get("neighbourhood") or "—"
            r[3].text = intel.get("primary_service", "—")
    else:
        doc.add_paragraph("No HIGH priority prospects in this report.")

    doc.add_paragraph()
    _heading(doc, "Medium Priority Prospects", level=2)
    if medium:
        for p in medium[:10]:
            biz = p["business"]
            doc.add_paragraph(
                f"• {biz.get('name')} ({biz.get('neighbourhood') or 'Nairobi'}) — "
                f"{p['intelligence'].get('primary_service', '—')}",
                style="List Bullet"
            )
    else:
        doc.add_paragraph("No MEDIUM priority prospects in this report.")

    doc.add_paragraph()
    _heading(doc, "Practical Recommendations", level=2)
    recs = [
        f"Target 3–5 HIGH priority outreaches per day maximum — quality over quantity.",
        f"Always verify contact details manually before reaching out.",
        f"Review the website audit findings before calling — be specific, not generic.",
        f"Reference your portfolio: {AGENCY_URL}",
        f"Respect opt-outs immediately — mark DNC in the system and stop contact.",
        f"Focus first on businesses with both a phone number and a website weakness.",
        f"Follow up at most once per business, unless they respond positively.",
        f"Track every outreach attempt — even 'no responses' are useful data.",
    ]
    for r in recs:
        doc.add_paragraph(f"• {r}", style="List Bullet")

    doc.add_paragraph()
    _heading(doc, "Research Methodology & Limitations", level=2)
    doc.add_paragraph(
        "Business records were discovered using the OpenStreetMap Overpass API, covering "
        "an approximate Nairobi County envelope. OSM data is community-contributed and may "
        "not include every business in Nairobi, particularly newer or informal businesses. "
        "Website status was checked by automated HTTP request at the time of report generation. "
        "A website that was reachable during checking may not be reachable later, and vice versa. "
        "Contact details are sourced from OSM public tags only. Do not treat any finding as "
        "definitive without manual verification. This report is a research starting point, "
        "not a conclusive audit."
    )

    doc.add_paragraph()
    _heading(doc, "Source References", level=2)
    sources = [
        ("OpenStreetMap", "https://www.openstreetmap.org", "ODbL licence — https://www.openstreetmap.org/copyright"),
        ("Overpass API", "https://overpass-api.de", "Public research use"),
        ("Nominatim Geocoding", "https://nominatim.openstreetmap.org", "ODbL — for neighbourhood reverse geocoding"),
    ]
    for name, url, note in sources:
        p = doc.add_paragraph()
        p.add_run(f"{name}: ").bold = True
        _add_hyperlink(p, url, url)
        p.add_run(f" — {note}")


# ---------------------------------------------------------------------------
# Main report generator
# ---------------------------------------------------------------------------

def generate_report(
    prospects: list[dict[str, Any]],
    stats: dict[str, Any],
    output_dir: str = "reports",
) -> Path:
    """
    Generate a Word (.docx) prospect report.

    prospects: list of dicts, each with keys: business, intelligence, outreach
    stats:     summary statistics dict
    output_dir: directory to save the report

    Returns the Path to the generated file.
    """
    now    = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    fname  = f"ProspectIQ_Nairobi_Prospect_Report_{date_str}.docx"

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / fname

    log.info("Generating Word report: %s (%d prospects)", out_path, len(prospects))

    doc = Document()

    # Page setup — A4
    from docx.shared import Mm
    section = doc.sections[0]
    section.page_width  = Mm(210)
    section.page_height = Mm(297)
    section.left_margin   = Inches(1.0)
    section.right_margin  = Inches(1.0)
    section.top_margin    = Inches(1.0)
    section.bottom_margin = Inches(1.0)

    # Header
    header = section.header
    hp = header.paragraphs[0]
    hp.text = f"{AGENCY_NAME} | ProspectIQ Nairobi Report {date_str}"
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in hp.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = GREY_TEXT

    # Footer
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.add_run(f"{AGENCY_NAME} — {AGENCY_URL} | Confidential research report").font.size = Pt(9)

    # ── Sections ──
    _cover_page(doc, date_str, len(prospects))

    if not prospects:
        _heading(doc, "No Qualified Prospects Found", level=1)
        doc.add_paragraph(
            "The discovery and verification pipeline did not find any businesses that "
            "passed the qualification criteria for this run. This may mean:\n"
            "• The discovery area was too small.\n"
            "• All discovered businesses had verified, high-quality websites.\n"
            "• Insufficient contact data was available.\n\n"
            "Recommendation: Run a full Nairobi County sweep (python -m prospectiq.cli sweep) "
            "and then run the pipeline again."
        )
    else:
        _executive_summary(doc, stats)
        _market_overview(doc, stats)

        _heading(doc, "Prioritised Prospect Directory", level=1)
        doc.add_paragraph(
            f"The following {len(prospects)} businesses have been identified as qualified "
            f"prospects for {AGENCY_NAME} services. They are sorted by lead score "
            f"(highest first). Each profile is based entirely on verified, publicly available data."
        )
        _page_break(doc)

        for i, prospect in enumerate(prospects, 1):
            _prospect_section(doc, prospect, i)

        _action_plan(doc, prospects)

    doc.save(out_path)
    log.info("Report saved: %s", out_path)
    return out_path
