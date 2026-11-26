"""
Exploratory: dump every table pdfplumber detects on some pages of a bronze PDF.

Writes data/2_silver/raw-tables/<doc_id>/page-NNNN/table-NN.csv plus
data/2_silver/raw-tables/<doc_id>.manifest.jsonl. Use it to look at a document's
layout while writing its extraction spec; the pipeline itself reads tables with
extract_statement_tables.py, driven by config/extraction/<doc_id>.yaml.

Usage:
  python src/extract/extract_tables.py --doc-id fed-canada-public-accounts-2024-25-vol2 --pages 11-12
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import SILVER, doc_path, manifest_doc, rel  # noqa: E402


@dataclass(frozen=True)
class TableRecord:
    doc_id: str
    pdf_path: str
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
    doc_id: str,
    pdf_path: Path,
    out_dir: Path,
    pages: str,
    table_settings: dict[str, Any] | None,
) -> list[TableRecord]:
    records: list[TableRecord] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        page_count = len(pdf.pages)
        for page_number in _iter_page_numbers(page_count, pages):
            page = pdf.pages[page_number - 1]
            tables = page.find_tables(table_settings=table_settings) if table_settings else page.find_tables()
            for i, table in enumerate(tables, start=1):
                rows = table.extract() or []
                csv_path = out_dir / doc_id / f"page-{page_number:04d}" / f"table-{i:02d}.csv"
                nrows, ncols = _write_csv(csv_path, rows)
                records.append(
                    TableRecord(
                        doc_id=doc_id,
                        pdf_path=rel(pdf_path),
                        page_number=page_number,
                        table_index=i,
                        bbox=[float(x) for x in table.bbox],
                        nrows=nrows,
                        ncols=ncols,
                        csv_path=rel(csv_path),
                    )
                )

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--doc-id", required=True, help="Document id from data/1_bronze/source-docs-manifest.yaml")
    parser.add_argument("--out", type=Path, default=SILVER / "raw-tables", help="Output root (default: data/2_silver/raw-tables)")
    parser.add_argument("--pages", default="all", help='Pages selector: "all", "1-5", or "1,3,10-12" (default: all)')
    parser.add_argument("--table-settings-json", type=str, default="", help="Optional JSON object for pdfplumber table_settings")
    args = parser.parse_args()

    table_settings = json.loads(args.table_settings_json) if args.table_settings_json.strip() else None
    pdf_path = doc_path(manifest_doc(args.doc_id))
    manifest_path = args.out / f"{args.doc_id}.manifest.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    records = extract_tables(
        doc_id=args.doc_id,
        pdf_path=pdf_path,
        out_dir=args.out,
        pages=args.pages,
        table_settings=table_settings,
    )

    with manifest_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")

    print(f"Extracted {len(records)} tables")
    print(f"Manifest: {rel(manifest_path)}")


if __name__ == "__main__":
    main()
