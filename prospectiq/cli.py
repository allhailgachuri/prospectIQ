"""
ProspectIQ command-line interface.

Commands
--------
discover   Fetch named businesses from OpenStreetMap (single bbox).
sweep      Run a full tiled Nairobi County discovery sweep.
check      Verify website status and run quality audits.
pipeline   Run the full pipeline: discover → check → report.
report     Generate a Word prospect report from the current database.
stats      Print database summary statistics.
export     Export all stored businesses to CSV.

Examples
--------
# Quick test on a small area
python -m prospectiq.cli discover --bbox "-1.28,36.78,-1.25,36.82"

# Full Nairobi County sweep (takes ~20-30 min; respectful of API)
python -m prospectiq.cli sweep

# Check websites for businesses in the database
python -m prospectiq.cli check --limit 100

# Generate Word report
python -m prospectiq.cli report

# Run everything end to end
python -m prospectiq.cli pipeline
"""
import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from .config import DEFAULT_BBOX, AGENCY_NAME, AGENCY_URL
from .logger import configure_logging, get_logger
from .normalize import normalize_element
from .overpass import fetch_business_elements
from .storage import (
    count_businesses,
    export_csv,
    get_stats,
    get_businesses_for_website_check,
    get_qualified_prospects,
    initialize_database,
    update_website_check,
    upsert_many,
)

configure_logging()
log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Argument helpers
# ---------------------------------------------------------------------------

def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    try:
        parts = tuple(float(x.strip()) for x in value.split(","))
        if len(parts) != 4:
            raise ValueError("Expected exactly 4 values.")
        s, w, n, e = parts
        if s >= n:
            raise ValueError("south must be less than north.")
        if w >= e:
            raise ValueError("west must be less than east.")
        return parts  # type: ignore[return-value]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid bbox '{value}': {exc}  "
            "Format: south,west,north,east  (e.g. -1.30,36.75,-1.25,36.90)"
        ) from exc


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------

def _cmd_discover(args: argparse.Namespace) -> int:
    bbox = args.bbox
    log.info("Starting discovery for bbox: %.4f, %.4f, %.4f, %.4f", *bbox)

    try:
        elements = fetch_business_elements(bbox)
    except RuntimeError as exc:
        log.error("Discovery failed: %s", exc)
        print(
            f"\n[ERROR] Could not reach the Overpass API.\n"
            f"  Detail: {exc}\n"
            "  Possible causes: no internet, API at capacity, query too large.\n"
            "  Try a smaller --bbox or wait a few minutes and retry.\n"
        )
        return 1

    records = []
    skipped = 0
    for element in elements:
        try:
            rec = normalize_element(element)
            if rec:
                records.append(rec)
            else:
                skipped += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("Normalisation error on element %s: %s", element.get("id"), exc)
            skipped += 1

    saved  = upsert_many(records)
    total  = count_businesses()

    print(
        f"\n✓ Discovery complete.\n"
        f"  Elements received : {len(elements)}\n"
        f"  Records normalised: {len(records)}\n"
        f"  Records upserted  : {saved}\n"
        f"  Total in database : {total}\n"
    )
    return 0


# ---------------------------------------------------------------------------
# sweep
# ---------------------------------------------------------------------------

def _cmd_sweep(args: argparse.Namespace) -> int:
    from .tiles import run_full_sweep, count_tiles, NAIROBI_SOUTH, NAIROBI_WEST, NAIROBI_NORTH, NAIROBI_EAST, TILE_SIZE

    total = count_tiles()
    print(
        f"\n Starting full Nairobi County sweep.\n"
        f"  Tiles to process : {total}\n"
        f"  Estimated time   : {total * 10 // 60}–{total * 15 // 60} minutes\n"
        f"  Sleep between tiles: 8 seconds (respectful of public API)\n"
        f"\n  Press Ctrl+C at any time — progress is saved to the database.\n"
    )

    def _progress(idx, total_tiles, bbox):
        pct = idx * 100 // total_tiles
        print(f"  [{pct:3d}%] Tile {idx}/{total_tiles} bbox={bbox}", flush=True)

    try:
        summary = run_full_sweep(progress_callback=_progress)
    except KeyboardInterrupt:
        print("\n  Sweep interrupted. Progress has been saved.")
        return 0

    print(
        f"\n✓ Sweep complete.\n"
        f"  Tiles processed  : {summary['total_tiles'] - summary['tile_errors']}/{summary['total_tiles']}\n"
        f"  Tile errors      : {summary['tile_errors']}\n"
        f"  Elements received: {summary['total_elements']}\n"
        f"  Records stored   : {summary['total_records']}\n"
        f"  Total in database: {summary['db_total']}\n"
    )
    return 0


# ---------------------------------------------------------------------------
# check (website verification + audit)
# ---------------------------------------------------------------------------

def _cmd_check(args: argparse.Namespace) -> int:
    from .website import check_business_website, STATUS_UNKNOWN

    limit = args.limit
    businesses = get_businesses_for_website_check(limit=limit)

    if not businesses:
        print("No businesses pending website check.")
        return 0

    print(
        f"\n Checking websites for {len(businesses)} businesses...\n"
        f"  (This sends one request per business — please be patient)\n"
    )

    checked = 0
    verified = 0
    unreachable = 0
    not_found = 0

    for i, biz in enumerate(businesses, 1):
        name = biz.get("name", "?")
        try:
            result = check_business_website(biz)
            update_website_check(result)

            status = result.get("website_status", STATUS_UNKNOWN)
            if status == "VERIFIED_WEBSITE":
                verified += 1
                score_str = f" (audit: {result.get('audit_score')}/100)" if result.get("audit_score") is not None else ""
                print(f"  [{i}/{len(businesses)}] ✓ VERIFIED  {name}{score_str}")
            elif status == "WEBSITE_UNREACHABLE":
                unreachable += 1
                print(f"  [{i}/{len(businesses)}] ✗ UNREACHABLE  {name}")
            elif status == "WEBSITE_NOT_FOUND_AFTER_CHECKS":
                not_found += 1
                print(f"  [{i}/{len(businesses)}] — NO WEBSITE  {name}")
            else:
                print(f"  [{i}/{len(businesses)}] ? {status}  {name}")

            checked += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("Website check failed for %s: %s", name, exc)

    print(
        f"\n✓ Website checks complete.\n"
        f"  Checked     : {checked}\n"
        f"  Verified    : {verified}\n"
        f"  Unreachable : {unreachable}\n"
        f"  No website  : {not_found}\n"
    )
    return 0


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def _cmd_report(args: argparse.Namespace) -> int:
    from .intelligence import analyse_business
    from .outreach import build_outreach_package
    from .report import generate_report

    limit = getattr(args, "limit", 50)
    output_dir = getattr(args, "output_dir", "reports")

    print(f"\n Qualifying prospects and building report (limit: {limit})...")

    raw_prospects = get_qualified_prospects(limit=limit)

    if not raw_prospects:
        print(
            "\n  No qualified prospects found in the database.\n"
            "  Run 'discover' or 'sweep' first to populate the database,\n"
            "  then run 'check' to verify website status.\n"
        )
        # Still generate a report explaining the situation
        raw_prospects = []

    print(f"  Analysing {len(raw_prospects)} prospects...")

    prospects = []
    for biz in raw_prospects:
        try:
            intel    = analyse_business(biz)
            outreach = build_outreach_package(biz, intel)
            prospects.append({
                "business":    biz,
                "intelligence": intel,
                "outreach":    outreach,
            })
        except Exception as exc:  # noqa: BLE001
            log.warning("Analysis failed for %s: %s", biz.get("name"), exc)

    # Sort by lead score
    prospects.sort(key=lambda p: p["intelligence"].get("lead_score", 0), reverse=True)

    # Build stats
    db_stats = get_stats()
    report_stats = {
        "total_discovered": db_stats["total"],
        "total_unique":     db_stats["total"],
        "with_email":       db_stats["with_email"],
        "with_phone":       db_stats["with_phone"],
        "by_category":      db_stats["by_category"],
        "by_neighbourhood": db_stats["by_neighbourhood"],
        "qualified":        len(prospects),
        "high_priority":    sum(1 for p in prospects if p["intelligence"]["priority"] == "HIGH"),
        "medium_priority":  sum(1 for p in prospects if p["intelligence"]["priority"] == "MEDIUM"),
        "needs_review":     sum(1 for p in prospects if p["intelligence"]["priority"] == "NEEDS_MANUAL_REVIEW"),
        "verified_websites":sum(1 for p in prospects if p["business"].get("website_status") == "VERIFIED_WEBSITE"),
        "no_website":       sum(1 for p in prospects if p["business"].get("website_status") == "WEBSITE_NOT_FOUND_AFTER_CHECKS"
                                or p["business"].get("website_presence") == "not_listed_in_osm"),
        "unreachable":      sum(1 for p in prospects if p["business"].get("website_status") == "WEBSITE_UNREACHABLE"),
        "weak_website":     sum(1 for p in prospects
                                if p["business"].get("audit_quality_label") in ("POOR", "WEAK")),
    }

    print(f"  Generating Word report...")
    out_path = generate_report(prospects, report_stats, output_dir=output_dir)

    print(
        f"\n✓ Report generated.\n"
        f"  File     : {out_path}\n"
        f"  Prospects: {len(prospects)}\n"
        f"  Priority breakdown:\n"
        f"    HIGH   : {report_stats['high_priority']}\n"
        f"    MEDIUM : {report_stats['medium_priority']}\n"
        f"    REVIEW : {report_stats['needs_review']}\n"
        f"\n  Open the .docx file to review your prospect intelligence report.\n"
        f"  Agency link in every outreach: {AGENCY_URL}\n"
    )
    return 0


# ---------------------------------------------------------------------------
# pipeline (full end-to-end)
# ---------------------------------------------------------------------------

def _cmd_pipeline(args: argparse.Namespace) -> int:
    """Run discover → check → report in one command."""
    bbox = getattr(args, "bbox", DEFAULT_BBOX)
    sweep = getattr(args, "sweep", False)

    print(
        f"\n{'='*60}\n"
        f"  ProspectIQ Full Pipeline\n"
        f"  {AGENCY_NAME} — {AGENCY_URL}\n"
        f"{'='*60}\n"
    )

    # Step 1: Discovery
    if sweep:
        print("\n[STEP 1/3] Running full Nairobi County sweep...")
        rc = _cmd_sweep(args)
    else:
        print(f"\n[STEP 1/3] Discovering businesses (bbox: {bbox})...")
        args.bbox = bbox
        rc = _cmd_discover(args)
    if rc != 0:
        return rc

    # Step 2: Website checks
    print(f"\n[STEP 2/3] Checking websites (up to {args.check_limit} businesses)...")
    check_args = argparse.Namespace(limit=args.check_limit)
    rc = _cmd_check(check_args)
    if rc != 0:
        return rc

    # Step 3: Report
    print(f"\n[STEP 3/3] Generating Word report (top {args.report_limit} prospects)...")
    report_args = argparse.Namespace(limit=args.report_limit, output_dir=args.output_dir)
    return _cmd_report(report_args)


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

def _cmd_stats(_args: argparse.Namespace) -> int:
    stats = get_stats()

    sep = "-" * 55
    print(f"\n{sep}")
    print(f"  ProspectIQ -- Database Statistics")
    print(sep)
    print(f"  Total businesses      : {stats['total']}")
    print(f"  With website (OSM)    : {stats['with_website']}")
    print(f"  Without website (OSM) : {stats['without_website']}")
    print(f"  With phone            : {stats['with_phone']}")
    print(f"  With email            : {stats['with_email']}")

    if stats["by_category"]:
        print(f"\n  {'Category':<25} Count")
        print(f"  {'-'*35}")
        for row in stats["by_category"]:
            cat = row["category"] or "(none)"
            print(f"  {cat:<25} {row['n']}")

    if stats["by_neighbourhood"]:
        print(f"\n  {'Neighbourhood':<30} Count")
        print(f"  {'-'*40}")
        for row in stats["by_neighbourhood"]:
            nb = row["neighbourhood"] or "(unknown)"
            print(f"  {nb:<30} {row['n']}")

    print(f"{sep}\n")
    return 0


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def _cmd_export(args: argparse.Namespace) -> int:
    output = getattr(args, "output", "exports/businesses.csv")
    count = export_csv(output)
    if count:
        print(f"✓ Exported {count} businesses to {output}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"ProspectIQ — Nairobi Business Discovery Engine for {AGENCY_NAME}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # discover
    p_discover = subparsers.add_parser("discover", help="Fetch businesses (single bbox)")
    p_discover.add_argument("--bbox", type=_parse_bbox, default=DEFAULT_BBOX, metavar="S,W,N,E")

    # sweep
    subparsers.add_parser("sweep", help="Full tiled Nairobi County sweep")

    # check
    p_check = subparsers.add_parser("check", help="Verify website status + quality audit")
    p_check.add_argument("--limit", type=int, default=200, metavar="N",
                         help="Max businesses to check (default: 200)")

    # report
    p_report = subparsers.add_parser("report", help="Generate Word prospect report")
    p_report.add_argument("--limit", type=int, default=50, metavar="N",
                          help="Max prospects to include (default: 50)")
    p_report.add_argument("--output-dir", dest="output_dir", default="reports",
                          help="Output directory (default: reports/)")

    # pipeline
    p_pipeline = subparsers.add_parser("pipeline", help="Full pipeline: discover → check → report")
    p_pipeline.add_argument("--bbox", type=_parse_bbox, default=DEFAULT_BBOX, metavar="S,W,N,E")
    p_pipeline.add_argument("--sweep", action="store_true",
                            help="Use full tiled sweep instead of single bbox")
    p_pipeline.add_argument("--check-limit", dest="check_limit", type=int, default=200,
                            metavar="N", help="Max websites to check (default: 200)")
    p_pipeline.add_argument("--report-limit", dest="report_limit", type=int, default=50,
                            metavar="N", help="Max prospects in report (default: 50)")
    p_pipeline.add_argument("--output-dir", dest="output_dir", default="reports")

    # stats
    subparsers.add_parser("stats", help="Show database statistics")

    # export
    p_export = subparsers.add_parser("export", help="Export all records to CSV")
    p_export.add_argument("--output", default="exports/businesses.csv", metavar="PATH")

    args = parser.parse_args()
    initialize_database()

    handlers = {
        "discover": _cmd_discover,
        "sweep":    _cmd_sweep,
        "check":    _cmd_check,
        "report":   _cmd_report,
        "pipeline": _cmd_pipeline,
        "stats":    _cmd_stats,
        "export":   _cmd_export,
    }
    exit_code = handlers[args.command](args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
