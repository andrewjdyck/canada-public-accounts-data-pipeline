"""
Search for text within a PDF (useful to locate schedules / statement pages).

Requires: pdfplumber
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pdfplumber


def main() -> None:
    parser = argparse.ArgumentParser(description="Find pages containing a text/regex pattern.")
    parser.add_argument("--pdf", required=True, type=Path, help="Path to PDF")
    parser.add_argument("--pattern", required=True, help="Regex pattern (Python re)")
    parser.add_argument("--ignore-case", action="store_true", help="Case-insensitive search")
    parser.add_argument("--max-pages", type=int, default=0, help="Stop after scanning N pages (0 = all)")
    parser.add_argument("--max-matches", type=int, default=50, help="Stop after emitting N matches")
    parser.add_argument("--context", type=int, default=60, help="Context chars around first match on a page")
    args = parser.parse_args()

    flags = re.IGNORECASE if args.ignore_case else 0
    rx = re.compile(args.pattern, flags=flags)

    matches = 0
    with pdfplumber.open(str(args.pdf)) as pdf:
        total_pages = len(pdf.pages)
        limit = args.max_pages if args.max_pages and args.max_pages > 0 else total_pages
        for i in range(min(limit, total_pages)):
            page_number = i + 1
            text = pdf.pages[i].extract_text() or ""
            m = rx.search(text)
            if not m:
                continue
            start = max(0, m.start() - args.context)
            end = min(len(text), m.end() + args.context)
            snippet = " ".join(text[start:end].split())
            print(f"{page_number}\t{snippet}")
            matches += 1
            if matches >= args.max_matches:
                break


if __name__ == "__main__":
    main()


