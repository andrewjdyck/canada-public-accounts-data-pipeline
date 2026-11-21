"""
Scan a PDF and report which pages appear to contain tables (per pdfplumber).

Requires: pdfplumber
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pdfplumber


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a PDF for detectable tables.")
    parser.add_argument("--pdf", required=True, type=Path, help="Path to PDF")
    parser.add_argument("--every", type=int, default=1, help="Check every N pages (default: 1)")
    parser.add_argument("--start", type=int, default=1, help="Start page (1-based)")
    parser.add_argument("--end", type=int, default=0, help="End page (1-based, 0 = last)")
    parser.add_argument(
        "--table-settings-json",
        type=str,
        default="",
        help='Optional JSON object to pass as pdfplumber table_settings',
    )
    parser.add_argument("--min-tables", type=int, default=1, help="Only emit pages with >= this many tables")
    parser.add_argument("--max-output", type=int, default=200, help="Stop after emitting N pages")
    args = parser.parse_args()

    if args.every < 1:
        raise SystemExit("--every must be >= 1")

    table_settings: dict[str, Any] | None = json.loads(args.table_settings_json) if args.table_settings_json.strip() else None

    emitted = 0
    with pdfplumber.open(str(args.pdf)) as pdf:
        page_count = len(pdf.pages)
        start = max(1, args.start)
        end = args.end if args.end and args.end > 0 else page_count
        end = min(end, page_count)
        for page_number in range(start, end + 1, args.every):
            page = pdf.pages[page_number - 1]
            tables = page.find_tables(table_settings=table_settings) if table_settings else page.find_tables()
            if len(tables) < args.min_tables:
                continue
            text_chars = len(page.extract_text() or "")
            print(f"{page_number}\ttables={len(tables)}\ttext_chars={text_chars}")
            emitted += 1
            if emitted >= args.max_output:
                break


if __name__ == "__main__":
    main()


