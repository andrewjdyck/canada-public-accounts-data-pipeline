"""
Extract tables from a PDF into CSV files + a JSONL manifest.

This is intentionally "low dependency": only `pdfplumber` is required.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pdfplumber


@dataclass(frozen=True)
class TableRecord:
    pdf_path: str
    pdf_stem: str
    page_number: int  # 1-based
    table_index: int  # 1-based within page
    bbox: list[float]  # [x0, top, x1, bottom]
    nrows: int
    ncols: int
    csv_path: str


def _iter_page_numbers(page_count: int, pages: str) -> Iterable[int]:
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


def _write_csv(path: Path, rows: list[list[str | None]]) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    ncols = max((len(r) for r in rows), default=0)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for r in rows:
            # normalize ragged rows
            rr = list(r) + [""] * max(0, ncols - len(r))
            w.writerow(["" if c is None else str(c) for c in rr])
    return (len(rows), ncols)


def extract_tables(
    pdf_path: Path,
    out_dir: Path,
    pages: str,
    table_settings: dict[str, Any] | None,
) -> list[TableRecord]:
    records: list[TableRecord] = []
    pdf_stem = pdf_path.stem

    with pdfplumber.open(str(pdf_path)) as pdf:
        page_count = len(pdf.pages)
        for page_number in _iter_page_numbers(page_count, pages):
            page = pdf.pages[page_number - 1]
            tables = page.find_tables(table_settings=table_settings) if table_settings else page.find_tables()
            for i, table in enumerate(tables, start=1):
                rows = table.extract() or []
                csv_path = out_dir / pdf_stem / f"page-{page_number:04d}" / f"table-{i:02d}.csv"
                nrows, ncols = _write_csv(csv_path, rows)
                records.append(
                    TableRecord(
                        pdf_path=str(pdf_path),
                        pdf_stem=pdf_stem,
                        page_number=page_number,
                        table_index=i,
                        bbox=[float(x) for x in table.bbox],
                        nrows=nrows,
                        ncols=ncols,
                        csv_path=str(csv_path),
                    )
                )

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract tables from a PDF into CSVs.")
    parser.add_argument("--pdf", required=True, type=Path, help="Path to PDF")
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output directory root (e.g. output-data/raw-tables)",
    )
    parser.add_argument(
        "--pages",
        default="all",
        help='Pages selector: "all", "1-5", or "1,3,10-12" (default: all)',
    )
    parser.add_argument(
        "--table-settings-json",
        type=str,
        default="",
        help='Optional JSON object to pass as pdfplumber table_settings',
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional path to write JSONL manifest (defaults to <out>/<pdf_stem>.manifest.jsonl)",
    )
    args = parser.parse_args()

    table_settings = json.loads(args.table_settings_json) if args.table_settings_json.strip() else None
    manifest_path = args.manifest or (args.out / f"{args.pdf.stem}.manifest.jsonl")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    records = extract_tables(
        pdf_path=args.pdf,
        out_dir=args.out,
        pages=args.pages,
        table_settings=table_settings,
    )

    with manifest_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")

    print(f"Extracted {len(records)} tables")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()


