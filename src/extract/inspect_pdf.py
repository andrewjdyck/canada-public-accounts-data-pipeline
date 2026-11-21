"""
Inspect a Public Accounts PDF to understand extractability:
- page count
- embedded text presence (chars per page)
- basic table detection counts per page

Designed to run with only `pdfplumber` installed (no pandas/numpy).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pdfplumber


@dataclass(frozen=True)
class PageSummary:
    page_number: int  # 1-based
    text_chars: int
    table_count: int


def _iter_page_numbers(page_count: int, pages: str) -> Iterable[int]:
    """
    Pages selector:
    - "all"
    - "1-5"
    - "1,3,10-12"
    """
    pages = pages.strip().lower()
    if pages == "all":
        return range(1, page_count + 1)

    selected: set[int] = set()
    for part in pages.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a)
            end = int(b)
            if end < start:
                start, end = end, start
            for p in range(start, end + 1):
                selected.add(p)
        else:
            selected.add(int(part))

    return (p for p in sorted(selected) if 1 <= p <= page_count)


def inspect_pdf(
    pdf_path: Path,
    pages: str,
    table_settings: dict[str, Any] | None,
    show_sample_page: int | None,
    max_sample_lines: int,
) -> dict[str, Any]:
    with pdfplumber.open(str(pdf_path)) as pdf:
        page_count = len(pdf.pages)
        doc_meta = pdf.metadata or {}

        summaries: list[PageSummary] = []
        for page_number in _iter_page_numbers(page_count, pages):
            page = pdf.pages[page_number - 1]

            text = page.extract_text() or ""
            text_chars = len(text)

            tables = page.find_tables(table_settings=table_settings) if table_settings else page.find_tables()
            summaries.append(PageSummary(page_number=page_number, text_chars=text_chars, table_count=len(tables)))

        sample: dict[str, Any] | None = None
        if show_sample_page is not None and 1 <= show_sample_page <= page_count:
            page = pdf.pages[show_sample_page - 1]
            text = page.extract_text() or ""
            lines = text.splitlines()
            sample = {
                "page_number": show_sample_page,
                "text_first_lines": lines[:max_sample_lines],
            }
            tables = page.find_tables(table_settings=table_settings) if table_settings else page.find_tables()
            sample["tables_found"] = len(tables)
            if tables:
                t0 = tables[0]
                sample["first_table_bbox"] = list(t0.bbox)
                sample["first_table_preview_rows"] = (t0.extract() or [])[: min(10, len(t0.extract() or []))]

        return {
            "pdf_path": str(pdf_path),
            "pdf_metadata": doc_meta,
            "page_count": page_count,
            "pages_inspected": pages,
            "table_settings": table_settings,
            "page_summaries": [s.__dict__ for s in summaries],
            "sample": sample,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a public accounts PDF for extractability.")
    parser.add_argument("--pdf", required=True, type=Path, help="Path to PDF")
    parser.add_argument(
        "--pages",
        default="1-5",
        help='Pages selector: "all", "1-5", or "1,3,10-12" (default: 1-5)',
    )
    parser.add_argument(
        "--sample-page",
        type=int,
        default=1,
        help="Page number (1-based) to show a small text/table preview for (default: 1)",
    )
    parser.add_argument("--max-sample-lines", type=int, default=25, help="Max lines to show in preview")
    parser.add_argument(
        "--table-settings-json",
        type=str,
        default="",
        help='Optional JSON object to pass as pdfplumber table_settings (e.g. \'{"vertical_strategy":"lines"}\')',
    )
    args = parser.parse_args()

    table_settings = json.loads(args.table_settings_json) if args.table_settings_json.strip() else None

    report = inspect_pdf(
        pdf_path=args.pdf,
        pages=args.pages,
        table_settings=table_settings,
        show_sample_page=args.sample_page,
        max_sample_lines=args.max_sample_lines,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


