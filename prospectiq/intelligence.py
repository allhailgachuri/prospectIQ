"""
Business intelligence and lead scoring for ProspectIQ.

For each verified prospect:
  1. Determine the industry and what the business likely does.
  2. Identify which BuiltByRushion services it could realistically benefit from.
  3. Generate an explainable lead score (0–100) and priority tier.

This module reasons purely from OSM data + website audit results.
It does NOT invent facts.  Every claim is traceable to a data field.
"""
from typing import Any

from .config import AGENCY_NAME, AGENCY_URL
from .logger import get_logger
from .website import STATUS_VERIFIED, STATUS_NOT_FOUND, STATUS_UNREACHABLE, STATUS_UNKNOWN

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Industry mapping
# (OSM category + subcategory → human-readable industry label)
# ---------------------------------------------------------------------------

INDUSTRY_MAP: dict[str, str] = {
    # shop subcategories
    "supermarket": "Retail — Supermarket",
    "convenience": "Retail — Convenience Store",
    "clothes":     "Retail — Fashion & Clothing",
    "shoes":       "Retail — Footwear",
    "electronics": "Retail — Electronics",
    "furniture":   "Retail — Furniture & Home",
    "hardware":    "Retail — Hardware & Building",
    "butcher":     "Retail — Butchery & Meat",
    "bakery":      "Food & Beverage — Bakery",
    "florist":     "Retail — Florist",
    "gift":        "Retail — Gifts & Souvenirs",
    "jewellery":   "Retail — Jewellery",
    "cosmetics":   "Health & Beauty",
    "hairdresser": "Health & Beauty — Hair Salon",
    "beauty":      "Health & Beauty — Beauty Salon",
    "optician":    "Health — Optician",
    "pharmacy":    "Health — Pharmacy",
    "mobile_phone":"Retail — Mobile Phones & Accessories",
    "computer":    "Technology — Computer & IT",
    "car":         "Automotive",
    "car_repair":  "Automotive — Repair & Service",
    "fuel":        "Automotive — Fuel Station",
    "tyres":       "Automotive — Tyres",
    "books":       "Retail — Books & Stationery",
    "stationery":  "Retail — Stationery",
    "sports":      "Retail — Sports & Fitness",
    "toy":         "Retail — Toys & Games",
    "pet":         "Retail — Pet Supplies",
    "garden":      "Retail — Garden & Plants",
    "alcohol":     "Retail — Wine & Spirits",
    "general":     "Retail — General Merchandise",
    "wholesale":   "Wholesale & Distribution",
    # amenity subcategories
    "restaurant":  "Food & Beverage — Restaurant",
    "fast_food":   "Food & Beverage — Fast Food",
    "cafe":        "Food & Beverage — Café",
    "bar":         "Food & Beverage — Bar & Nightlife",
    "pub":         "Food & Beverage — Pub",
    "food_court":  "Food & Beverage — Food Court",
    "hospital":    "Healthcare — Hospital",
    "clinic":      "Healthcare — Clinic",
    "dentist":     "Healthcare — Dental",
    "doctors":     "Healthcare — General Practice",
    "pharmacy":    "Healthcare — Pharmacy",
    "veterinary":  "Healthcare — Veterinary",
    "bank":        "Financial Services — Bank",
    "atm":         "Financial Services — ATM",
    "bureau_de_change": "Financial Services — Currency Exchange",
    "insurance":   "Financial Services — Insurance",
    "microfinance":"Financial Services — Microfinance",
    "school":      "Education — School",
    "college":     "Education — College",
    "university":  "Education — University",
    "language_school": "Education — Language School",
    "driving_school":  "Education — Driving School",
    "gym":         "Health & Wellness — Gym / Fitness",
    "spa":         "Health & Wellness — Spa",
    "hotel":       "Hospitality — Hotel",
    "hostel":      "Hospitality — Hostel",
    "guest_house": "Hospitality — Guest House",
    "place_of_worship": "Religious Organisation",
    "cinema":      "Entertainment — Cinema",
    "theatre":     "Entertainment — Theatre",
    "events_venue":"Events — Venue",
    "nightclub":   "Entertainment — Nightclub",
    "laundry":     "Services — Laundry",
    "dry_cleaning":"Services — Dry Cleaning",
    "post_office": "Services — Post Office",
    "police":      "Government — Police",
    "fire_station":"Government — Fire Station",
    "embassy":     "Government — Embassy",
    "courthouse":  "Government — Courthouse",
    "car_rental":  "Automotive — Car Rental",
    "car_wash":    "Automotive — Car Wash",
    "parking":     "Automotive — Parking",
    "fuel":        "Automotive — Fuel Station",
    "taxi":        "Transport — Taxi",
    "bus_station": "Transport — Bus / Matatu",
    "marketplace": "Retail — Market",
    # office subcategories
    "company":     "Corporate — Company",
    "it":          "Technology — IT Company",
    "accountant":  "Professional Services — Accounting",
    "lawyer":      "Professional Services — Legal",
    "architect":   "Professional Services — Architecture",
    "estate_agent":"Real Estate",
    "ngo":         "Non-Profit / NGO",
    "government":  "Government",
    "newspaper":   "Media — Newspaper",
    "logistics":   "Logistics & Supply Chain",
    "travel_agent":"Tourism — Travel Agency",
    "advertising": "Marketing & Advertising",
    "marketing":   "Marketing & Advertising",
    "consulting":  "Consulting",
    # tourism
    "hotel":       "Hospitality — Hotel",
    "museum":      "Tourism — Museum",
    "attraction":  "Tourism — Attraction",
    "gallery":     "Arts — Gallery",
    # healthcare
    "doctor":      "Healthcare — General Practice",
    "hospital":    "Healthcare — Hospital",
    # craft
    "tailor":      "Fashion — Tailor",
    "shoemaker":   "Fashion — Cobbler",
    "carpenter":   "Trade — Carpenter",
    "electrician": "Trade — Electrician",
    "plumber":     "Trade — Plumber",
    "welder":      "Trade — Welder",
    "printer":     "Printing & Graphics",
    "photographer":"Creative — Photography",
}

# Category → general industry (fallback when subcategory not in map)
CATEGORY_INDUSTRY: dict[str, str] = {
    "shop":       "Retail",
    "amenity":    "Services",
    "office":     "Professional Services",
    "craft":      "Trade & Craft",
    "healthcare": "Healthcare",
    "tourism":    "Hospitality & Tourism",
    "leisure":    "Leisure & Recreation",
    "restaurant": "Food & Beverage",
    "hotel":      "Hospitality",
    "clinic":     "Healthcare",
}

# ---------------------------------------------------------------------------
# Service opportunity definitions
# ---------------------------------------------------------------------------

SERVICES: dict[str, str] = {
    "website_new":       "New Business Website",
    "website_redesign":  "Website Redesign",
    "ecommerce":         "E-Commerce / Online Shop",
    "booking_system":    "Online Booking or Reservation System",
    "management_system": "Custom Business Management System",
    "analytics":         "Business Analytics & Dashboard",
    "automation":        "Workflow / Reporting Automation",
    "crm":               "Customer Relationship Management (CRM)",
    "inventory":         "Inventory Management System",
    "mobile_app":        "Mobile Application",
    "api_integration":   "API & System Integration",
}

# OSM subcategory → list of likely service opportunities
SUBCATEGORY_SERVICES: dict[str, list[str]] = {
    "restaurant":    ["website_new", "website_redesign", "booking_system", "analytics"],
    "fast_food":     ["website_new", "ecommerce", "analytics"],
    "cafe":          ["website_new", "booking_system", "analytics"],
    "hotel":         ["website_redesign", "booking_system", "analytics", "crm"],
    "guest_house":   ["website_new", "booking_system"],
    "hostel":        ["website_new", "booking_system"],
    "clinic":        ["website_new", "booking_system", "management_system", "crm"],
    "hospital":      ["website_redesign", "management_system", "analytics", "crm"],
    "doctors":       ["website_new", "booking_system"],
    "dentist":       ["website_new", "booking_system", "crm"],
    "pharmacy":      ["website_new", "ecommerce", "inventory"],
    "school":        ["website_new", "management_system", "analytics"],
    "college":       ["website_redesign", "management_system", "analytics"],
    "university":    ["website_redesign", "analytics", "automation"],
    "supermarket":   ["website_new", "ecommerce", "inventory", "analytics"],
    "convenience":   ["website_new", "ecommerce", "inventory"],
    "clothes":       ["website_new", "ecommerce"],
    "electronics":   ["website_new", "ecommerce", "inventory"],
    "furniture":     ["website_new", "ecommerce"],
    "hardware":      ["website_new", "ecommerce", "inventory"],
    "company":       ["website_redesign", "analytics", "automation", "crm"],
    "it":            ["website_redesign", "analytics"],
    "accountant":    ["website_new", "automation", "analytics"],
    "lawyer":        ["website_new", "crm"],
    "estate_agent":  ["website_new", "crm", "analytics"],
    "bank":          ["website_redesign", "analytics", "automation"],
    "gym":           ["website_new", "booking_system", "crm"],
    "spa":           ["website_new", "booking_system", "crm"],
    "car_repair":    ["website_new", "management_system", "crm"],
    "travel_agent":  ["website_new", "booking_system", "crm"],
    "ngo":           ["website_new", "analytics", "automation"],
    "marketplace":   ["website_new", "ecommerce", "analytics"],
    "events_venue":  ["website_new", "booking_system", "crm"],
    "advertising":   ["website_redesign", "analytics"],
    "logistics":     ["website_new", "management_system", "analytics", "automation"],
    "printer":       ["website_new", "ecommerce"],
    "tailor":        ["website_new", "ecommerce"],
}

# Category-level fallback services
CATEGORY_SERVICES: dict[str, list[str]] = {
    "shop":       ["website_new", "ecommerce"],
    "amenity":    ["website_new"],
    "office":     ["website_new", "analytics"],
    "craft":      ["website_new"],
    "healthcare": ["website_new", "booking_system"],
    "tourism":    ["website_new", "booking_system"],
    "leisure":    ["website_new", "booking_system"],
}


def _get_industry(category: str | None, subcategory: str | None) -> str:
    """Derive a human-readable industry label."""
    if subcategory and subcategory.lower() in INDUSTRY_MAP:
        return INDUSTRY_MAP[subcategory.lower()]
    if category and category.lower() in CATEGORY_INDUSTRY:
        return CATEGORY_INDUSTRY[category.lower()]
    return "General Business"


def _get_services(category: str | None, subcategory: str | None) -> list[str]:
    """Return service opportunity keys for this business type."""
    if subcategory and subcategory.lower() in SUBCATEGORY_SERVICES:
        return SUBCATEGORY_SERVICES[subcategory.lower()]
    if category and category.lower() in CATEGORY_SERVICES:
        return CATEGORY_SERVICES[category.lower()]
    return ["website_new"]


# ---------------------------------------------------------------------------
# Lead scoring
# ---------------------------------------------------------------------------

def score_prospect(business: dict[str, Any]) -> dict[str, Any]:
    """
    Compute an explainable lead score for a business.

    Score components (max 100):
      - Website situation     (0–40 pts)
      - Contact availability  (0–20 pts)
      - Evidence strength     (0–20 pts)
      - Business relevance    (0–20 pts)

    Returns a scoring dict.
    """
    score = 0
    reasons: list[str] = []
    deductions: list[str] = []

    # --- Website situation (40 pts) ---
    ws = business.get("website_status") or business.get("website_presence", "")

    if ws in (STATUS_NOT_FOUND, "not_listed_in_osm", "WEBSITE_NOT_FOUND_AFTER_CHECKS"):
        score += 40
        reasons.append("No verifiable website found — strong new-website opportunity (+40)")
    elif ws == STATUS_UNREACHABLE:
        score += 35
        reasons.append("Website exists but is unreachable — urgent fix or redesign needed (+35)")
    elif ws == STATUS_VERIFIED:
        audit_score = business.get("audit_score")
        if audit_score is not None:
            if audit_score < 40:
                score += 30
                reasons.append(f"Website has serious quality issues (audit score: {audit_score}/100) (+30)")
            elif audit_score < 60:
                score += 20
                reasons.append(f"Website has notable weaknesses (audit score: {audit_score}/100) (+20)")
            elif audit_score < 80:
                score += 10
                reasons.append(f"Website could be improved (audit score: {audit_score}/100) (+10)")
            else:
                score += 0
                deductions.append(f"Website appears solid (audit score: {audit_score}/100) — website services less urgent")
        else:
            score += 15
            reasons.append("Website present but not yet fully audited (+15)")
    elif ws == STATUS_UNKNOWN:
        score += 20
        reasons.append("Website status not yet verified — needs checking (+20)")
    else:
        score += 20
        reasons.append("Website status unknown (+20)")

    # --- Contact availability (20 pts) ---
    contact_pts = 0
    if business.get("phone"):
        contact_pts += 8
        reasons.append("Public phone number available (+8)")
    if business.get("email"):
        contact_pts += 8
        reasons.append("Public email address available (+8)")
    if business.get("whatsapp"):
        contact_pts += 4
        reasons.append("WhatsApp contact published (+4)")
    if contact_pts == 0:
        deductions.append("No verified contact details — outreach will be harder")
    score += contact_pts

    # --- Evidence strength (20 pts) ---
    ev_pts = 0
    if business.get("latitude") and business.get("longitude"):
        ev_pts += 5
        reasons.append("Location coordinates verified in OSM (+5)")
    if business.get("address"):
        ev_pts += 5
        reasons.append("Street address available (+5)")
    if business.get("neighbourhood"):
        ev_pts += 5
        reasons.append("Neighbourhood confirmed (+5)")
    if business.get("description"):
        ev_pts += 5
        reasons.append("Business description available (+5)")
    score += ev_pts

    # --- Business relevance (20 pts) ---
    # Based on how well the business type matches our service offerings
    category = business.get("category", "")
    subcategory = business.get("subcategory", "")
    services = _get_services(category, subcategory)

    high_value_services = {
        "booking_system", "ecommerce", "management_system",
        "analytics", "crm", "inventory",
    }
    if any(s in high_value_services for s in services):
        score += 20
        reasons.append("Business type commonly benefits from high-value software services (+20)")
    elif "website_new" in services or "website_redesign" in services:
        score += 12
        reasons.append("Clear website development opportunity identified (+12)")
    else:
        score += 5
        reasons.append("General service opportunity (+5)")

    # Clamp
    score = max(0, min(100, score))

    # Priority tier
    if score >= 70:
        priority = "HIGH"
    elif score >= 45:
        priority = "MEDIUM"
    elif score >= 25:
        priority = "LOW"
    else:
        priority = "NEEDS_MANUAL_REVIEW"

    return {
        "lead_score":   score,
        "priority":     priority,
        "score_reasons":   reasons,
        "score_deductions": deductions,
    }


# ---------------------------------------------------------------------------
# Business profile
# ---------------------------------------------------------------------------

def analyse_business(business: dict[str, Any]) -> dict[str, Any]:
    """
    Build a complete intelligence profile for a single business.

    Returns a dict that will be used for outreach generation and reporting.
    """
    category = business.get("category")
    subcategory = business.get("subcategory")

    industry = _get_industry(category, subcategory)
    service_keys = _get_services(category, subcategory)
    services = [SERVICES[k] for k in service_keys if k in SERVICES]

    scoring = score_prospect(business)

    # Determine primary opportunity description
    ws = business.get("website_status") or business.get("website_presence", "")
    if ws in (STATUS_NOT_FOUND, "not_listed_in_osm", "WEBSITE_NOT_FOUND_AFTER_CHECKS"):
        opportunity = "No verifiable website found. This business is missing from the web."
        primary_service = SERVICES.get("website_new")
    elif ws == STATUS_UNREACHABLE:
        opportunity = "Website exists but is currently unreachable or broken."
        primary_service = SERVICES.get("website_redesign")
    elif ws == STATUS_VERIFIED:
        ql = business.get("audit_quality_label", "")
        recs = business.get("audit_recommendations", "")
        if ql in ("POOR", "WEAK"):
            opportunity = f"Website is live but has quality issues (rated {ql}). {recs or ''}"
            primary_service = SERVICES.get("website_redesign")
        elif ql == "FAIR":
            opportunity = f"Website exists and works, but has room for improvement."
            primary_service = services[1] if len(services) > 1 else services[0]
        else:
            opportunity = "Website appears functional. Primary opportunity may be in analytics or custom software."
            primary_service = services[1] if len(services) > 1 else services[0]
    else:
        opportunity = "Website status not yet fully verified. Manual review recommended."
        primary_service = SERVICES.get("website_new")

    # Build what-the-business-does description
    what_it_does = _describe_business(business, industry, subcategory)

    # Likely customers
    likely_customers = _infer_customers(industry, subcategory)

    return {
        "industry":         industry,
        "what_it_does":     what_it_does,
        "likely_customers": likely_customers,
        "services":         services,
        "primary_service":  primary_service,
        "opportunity":      opportunity,
        "lead_score":       scoring["lead_score"],
        "priority":         scoring["priority"],
        "score_reasons":    scoring["score_reasons"],
        "score_deductions": scoring["score_deductions"],
    }


def _describe_business(business: dict, industry: str, subcategory: str | None) -> str:
    """Generate a one-sentence description of what the business does."""
    name = business.get("name", "This business")
    desc = business.get("description")
    if desc:
        return f"{name} — {desc}"
    if subcategory:
        sub = subcategory.replace("_", " ").title()
        return f"{name} operates as a {sub} business in the {industry} sector."
    return f"{name} operates in the {industry} sector."


def _infer_customers(industry: str, subcategory: str | None) -> str:
    """Infer the likely customer base based on industry."""
    sub = (subcategory or "").lower()
    mapping = {
        "restaurant":   "Walk-in diners, office workers, and local residents",
        "hotel":        "Domestic and international travellers, corporate clients",
        "clinic":       "Local patients, families, and walk-in patients",
        "hospital":     "Patients, insurance providers, and referral doctors",
        "school":       "Students, parents, and guardians",
        "supermarket":  "Local households, businesses buying in bulk",
        "company":      "Corporate clients, businesses, and institutions",
        "gym":          "Health-conscious individuals, professionals",
        "bank":         "Individuals, SMEs, and corporate clients",
        "pharmacy":     "Patients, caregivers, and hospitals",
        "spa":          "Professionals, individuals seeking relaxation",
        "events_venue": "Event organisers, wedding planners, corporates",
        "lawyer":       "Individuals, businesses, and NGOs",
    }
    return mapping.get(sub, "Local businesses, individuals, and organisations in Nairobi")
