"""Generate a concise Excel outreach list for ProspectIQ prospects."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Side, Border
from openpyxl.utils import get_column_letter

from .intelligence import analyse_business
from .logger import get_logger

log = get_logger(__name__)

HEADERS = [
    "Business Name",
    "Phone (Call)",
    "WhatsApp (Text)",
    "Email",
    "Problem / Opportunity",
    "Solution (Brief)",
]


def generate_excel(
    prospects: list[dict[str, Any]],
    output_dir: str = "reports",
) -> Path:
    """Write one compact outreach worksheet and return its path."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"ProspectIQ_Outreach_{date_str}.xlsx"

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Outreach"
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:F{len(prospects) + 1}"

    header_fill = PatternFill("solid", fgColor="164E8A")
    header_font = Font(name="Aptos", bold=True, color="FFFFFF", size=10)
    border = Border(bottom=Side(style="thin", color="D8E3EB"))
    for column, heading in enumerate(HEADERS, 1):
        cell = sheet.cell(row=1, column=column, value=heading)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    sheet.row_dimensions[1].height = 30

    for row_index, prospect in enumerate(prospects, 2):
        business = prospect.get("business") or {}
        intelligence = prospect.get("intelligence") or analyse_business(business)
        row = [
            business.get("name") or "",
            business.get("phone") or "",
            business.get("whatsapp") or "",
            business.get("email") or "",
            intelligence.get("opportunity") or "",
            intelligence.get("primary_service") or "",
        ]
        for column, value in enumerate(row, 1):
            cell = sheet.cell(row=row_index, column=column, value=value)
            cell.font = Font(name="Aptos", size=10, color="183042")
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = border
            if row_index % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="F1F6FA")
        sheet.row_dimensions[row_index].height = 38

    widths = [30, 20, 20, 32, 54, 38]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    workbook.save(out_path)
    log.info("Generated outreach workbook: %s (%d prospects)", out_path, len(prospects))
    return out_path