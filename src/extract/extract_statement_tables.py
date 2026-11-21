"""
Extract financial-statement tables from a bronze PDF into silver, driven by a spec.

Reads config/extraction/<doc_id>.yaml (schema: config/extraction.schema.json) and,
for each table, writes data/silver/public-accounts/<doc_id>/<table_id>.csv in long
format: one row per (source row, source column) amount, labels kept as printed.
No categorisation happens here; that is the clean step's job (gold).

How a table part is read (method: pdfplumber_words):
  1. Group the page's words into lines by vertical position.
  2. Keep the lines between `start_after` and `end_at`.
  3. A "numeric line" is one ending in amount tokens (1,234 / (1,234) / dashes for nil).
     Text-only lines are label fragments (wrapped labels) and are attached to the next
     numeric line.
  4. Numeric lines are matched to the spec's `rows` in order; the count must agree.
  5. Each amount is assigned to a column by the x-position of its right edge, using the
     first numeric line that has one amount per column as the anchor.

Then the spec's `checks` (rows add to totals, columns add to totals) and `cross_checks`
(between tables) are run. Results go to data/silver/public-accounts/<doc_id>/checks.csv.
The script exits non-zero if any check fails, so a bad extraction never reaches gold.

Usage:
  python src/extract/extract_statement_tables.py --doc-id prov-on-public-accounts-2025-26
  python src/extract/extract_statement_tables.py --all
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import jsonschema
import pdfplumber
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import EXTRACTION_SCHEMA, EXTRACTION_SPECS, SILVER, doc_path, load_manifest, manifest_doc, rel  # noqa: E402

AMOUNT = re.compile(r"^(\(-?\$?[\d,]+(\.\d+)?\)|-?\$?[\d,]+(\.\d+)?)$")  # parentheses must balance
NIL = {"–", "-", "—", "−", "…", "...", "nil"}
LINE_TOLERANCE = 3.0  # points; words whose tops differ by less are on the same line
COLUMN_TOLERANCE = 30.0  # points; max distance from an amount's right edge to its column anchor

FIELDS = [
    "doc_id", "table_id", "page", "row_order", "row_label", "row_kind", "raw_label",
    "column_id", "column_kind", "fiscal_year", "basis", "column_dims",
    "value_as_printed", "amount", "scale", "currency",
]


def parse_amount(token: str) -> float | None:
    """'1,234' -> 1234; '(1,234)' -> -1234; dash -> 0. None if not an amount."""
    t = token.strip()
    if t in NIL:
        return 0.0
    if not AMOUNT.match(t):
        return None
    negative = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace("$", "").replace(",", "")
    v = float(t)
    return -v if negative else v


def page_lines(page) -> list[list[dict]]:
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=1.5)
    words.sort(key=lambda w: (round(w["top"]), w["x0"]))
    lines: list[list[dict]] = []
    for w in words:
        if lines and abs(lines[-1][0]["top"] - w["top"]) < LINE_TOLERANCE:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def split_line(line: list[dict]) -> tuple[str, list[dict]]:
    """Split a line into (label text, trailing amount words)."""
    amounts: list[dict] = []
    for w in reversed(line):
        if parse_amount(w["text"]) is None:
            break
        amounts.insert(0, w)
    label_words = line[: len(line) - len(amounts)]
    return " ".join(w["text"] for w in label_words), amounts


def label_score(expected: str, raw: str) -> float:
    words = lambda s: set(re.findall(r"[a-z]+", s.lower())) - {"and", "of", "the"}  # noqa: E731
    exp = words(expected)
    return len(exp & words(raw)) / len(exp) if exp else 1.0


def extract_part(pdf, table: dict, part: dict) -> list[dict]:
    page = pdf.pages[part["page"] - 1]
    lines = page_lines(page)
    texts = [" ".join(w["text"] for w in line) for line in lines]
    start = next((i for i, t in enumerate(texts) if re.search(part["start_after"], t)), None)
    if start is None:
        raise ValueError(f"page {part['page']}: start_after {part['start_after']!r} not found")
    end = next((i for i in range(start + 1, len(texts)) if re.search(part["end_at"], texts[i])), None)
    if end is None:
        raise ValueError(f"page {part['page']}: end_at {part['end_at']!r} not found")

    numeric: list[tuple[str, list[dict]]] = []
    pending: list[str] = []
    for line in lines[start + 1 : end + 1]:
        label, amounts = split_line(line)
        if not amounts:
            pending.append(label)
            continue
        numeric.append((" ".join(pending + [label]).strip(), amounts))
        pending = []

    rows, col_ids = table["rows"], part["columns"]
    if len(numeric) != len(rows):
        found = "\n    ".join(f"{r!r} ({len(a)} amounts)" for r, a in numeric)
        raise ValueError(f"page {part['page']}: expected {len(rows)} numeric lines, found {len(numeric)}:\n    {found}")

    anchor = next((a for _, a in numeric if len(a) == len(col_ids)), None)
    if anchor is None:
        raise ValueError(f"page {part['page']}: no line has one amount per column ({len(col_ids)}) to anchor columns")
    anchors = [w["x1"] for w in anchor]

    out = []
    for order, (row, (raw_label, amounts)) in enumerate(zip(rows, numeric), start=1):
        if label_score(row["label"], raw_label) < 0.5:
            raise ValueError(f"page {part['page']}: row {order} expected {row['label']!r}, text is {raw_label!r}")
        used: set[int] = set()
        for w in amounts:
            dist, idx = min((abs(w["x1"] - x), i) for i, x in enumerate(anchors))
            if dist > COLUMN_TOLERANCE or idx in used:
                raise ValueError(f"page {part['page']}: cannot place amount {w['text']!r} in row {row['label']!r}")
            used.add(idx)
            col_id = col_ids[idx]
            col = table["columns"][col_id]
            dims = {k: v for k, v in col.items() if k not in ("fiscal_year", "basis", "kind")}
            value = parse_amount(w["text"])
            out.append({
                "page": part["page"], "row_order": order, "row_label": row["label"],
                "row_kind": row.get("kind", "detail"), "raw_label": raw_label,
                "column_id": col_id, "column_kind": col.get("kind", "detail"),
                "fiscal_year": col["fiscal_year"], "basis": col["basis"],
                "column_dims": ";".join(f"{k}={v}" for k, v in dims.items()),
                "value_as_printed": w["text"], "amount": value,
            })
    return out


def run_checks(table: dict, cells: dict[tuple[str, str], float]) -> list[dict]:
    results = []
    row_kinds = {r["label"]: r.get("kind", "detail") for r in table["rows"]}
    detail_rows = [label for label, kind in row_kinds.items() if kind == "detail"]
    all_cols = list(table["columns"])
    for check in table.get("checks", []):
        tol = check.get("tolerance", 0)
        if check["type"] == "rows_sum":
            parts = check.get("rows", detail_rows)
            for col in check.get("columns", all_cols):
                if (check["equals"], col) not in cells:
                    continue
                got = sum(cells.get((r, col), 0.0) for r in parts)
                want = cells[(check["equals"], col)]
                results.append({"table_id": table["table_id"], "check": f"rows_sum -> {check['equals']}", "where": col,
                                "computed": got, "stated": want, "diff": got - want, "ok": abs(got - want) <= tol})
        elif check["type"] == "columns_sum":
            for row in check.get("for_rows", detail_rows):
                if (row, check["equals"]) not in cells:
                    continue
                got = sum(cells.get((row, c), 0.0) for c in check["columns"])
                want = cells[(row, check["equals"])]
                results.append({"table_id": table["table_id"], "check": f"columns_sum -> {check['equals']}", "where": row,
                                "computed": got, "stated": want, "diff": got - want, "ok": abs(got - want) <= tol})
    return results


def extract_doc(doc_id: str, manifest: dict) -> bool:
    spec_path = EXTRACTION_SPECS / f"{doc_id}.yaml"
    spec = yaml.safe_load(spec_path.read_text())
    jsonschema.validate(spec, json.loads(EXTRACTION_SCHEMA.read_text()))
    doc = manifest_doc(doc_id, manifest)
    pdf_path = doc_path(doc)
    out_dir = SILVER / "public-accounts" / doc_id
    out_dir.mkdir(parents=True, exist_ok=True)

    all_cells: dict[str, dict[tuple[str, str], float]] = {}
    checks: list[dict] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for table in spec["tables"]:
            rows: list[dict] = []
            for part in table["parts"]:
                rows += extract_part(pdf, table, part)
            scale, currency = table["units"]["scale"], table["units"]["currency"]
            for r in rows:
                r.update(doc_id=doc_id, table_id=table["table_id"], scale=scale, currency=currency)
            with (out_dir / f"{table['table_id']}.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(rows)
            cells = {(r["row_label"], r["column_id"]): r["amount"] for r in rows}
            all_cells[table["table_id"]] = cells
            checks += run_checks(table, cells)
            print(f"  {table['table_id']}: {len(rows)} amounts -> {rel(out_dir / (table['table_id'] + '.csv'))}")

    for cc in spec.get("cross_checks", []):
        left, right = cc["left"], cc["right"]
        a = all_cells[left["table"]].get((left["row"], left["column"]))
        b = all_cells[right["table"]].get((right["row"], right["column"]))
        ok = a is not None and b is not None and abs(a - b) <= cc.get("tolerance", 0)
        checks.append({"table_id": "(cross)", "check": f"{left['table']}[{left['row']}] = {right['table']}[{right['row']}]",
                       "where": f"{left['column']} vs {right['column']}", "computed": a, "stated": b,
                       "diff": None if a is None or b is None else a - b, "ok": ok})

    with (out_dir / "checks.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["table_id", "check", "where", "computed", "stated", "diff", "ok"])
        w.writeheader()
        w.writerows(checks)
    lineage = {
        "doc_id": doc_id, "source_file": rel(pdf_path), "source_sha256": doc["file"].get("sha256"),
        "spec_file": rel(spec_path), "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "method": "pdfplumber_words", "pdfplumber_version": pdfplumber.__version__,
        "extracted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / "lineage.json").write_text(json.dumps(lineage, indent=2) + "\n")

    failed = [c for c in checks if not c["ok"]]
    print(f"  checks: {len(checks) - len(failed)}/{len(checks)} passed")
    for c in failed:
        print(f"  FAIL {c['table_id']} {c['check']} at {c['where']}: computed {c['computed']} vs stated {c['stated']}")
    return not failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--doc-id", action="append", help="Document id (repeatable)")
    group.add_argument("--all", action="store_true", help="Every document with a spec in config/extraction/")
    args = parser.parse_args()

    manifest = load_manifest()
    doc_ids = args.doc_id or sorted(p.stem for p in EXTRACTION_SPECS.glob("*.yaml"))
    ok = True
    for doc_id in doc_ids:
        print(f"{doc_id}")
        try:
            ok = extract_doc(doc_id, manifest) and ok
        except ValueError as e:
            print(f"  ERROR {e}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
