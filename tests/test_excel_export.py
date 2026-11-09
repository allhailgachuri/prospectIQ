import os
import sys

from openpyxl import load_workbook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from prospectiq.excel_export import generate_excel


def test_export_contains_only_requested_outreach_fields(tmp_path):
    prospects = [
        {
            "business": {
                "name": "Sample Business",
                "phone": "+254700000000",
                "whatsapp": "+254711111111",
                "email": "hello@example.com",
            },
            "intelligence": {
                "opportunity": "No booking information is listed.",
                "primary_service": "Online booking system",
            },
        }
    ]

    path = generate_excel(prospects, output_dir=str(tmp_path))
    workbook = load_workbook(path, read_only=True)
    try:
        assert workbook.sheetnames == ["Outreach"]
        sheet = workbook.active
        assert [cell.value for cell in sheet[1]] == [
            "Business Name",
            "Phone (Call)",
            "WhatsApp (Text)",
            "Email",
            "Problem / Opportunity",
            "Solution (Brief)",
        ]
        assert [cell.value for cell in sheet[2]] == [
            "Sample Business",
            "+254700000000",
            "+254711111111",
            "hello@example.com",
            "No booking information is listed.",
            "Online booking system",
        ]
    finally:
        workbook.close()