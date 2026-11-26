"""
Federal Volume II transfer-payment tables -> data/2_silver/public-accounts/<doc_id>/transfer-payments.csv.

Each Volume II ministry section has a "Transfer payments" table (in dollars) listing every
program under its department or agency, grouped as Grants / Contributions / Other transfer
payments, with nine amount columns ending "Used in the current year", "Variance",
"Available for use in subsequent years", "Used in the previous year". Spec:
config/extraction/program-tables/<doc_id>.yaml (sections and page ranges).

How a section is read:
  - lines are built from word positions (same helpers as extract_statement_tables.py);
  - a numeric line ends in nine amounts; text-only lines before it are its wrapped label;
  - a text line "Grants", "Contributions" or "Other transfer payments" sets the transfer type,
    and any text just before it is the department/agency heading;
  - "Total..." lines are kept as totals for checking;
  - the section ends at "Total Ministry".

Check: for every section, program lines add to the "Total Ministry" line (used in current
year, to the dollar). The script exits non-zero if any section fails.

Usage:
  python src/extract/extract_vol2_transfers.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import pdfplumber
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract.extract_statement_tables import page_lines, parse_amount, split_line  # noqa: E402
from paths import CONFIG, SILVER, doc_path, load_manifest, manifest_doc, rel  # noqa: E402

TYPES = {"Grants": "grant", "Contributions": "contribution", "Other transfer payments": "other_transfer_payment"}
GROUPED = re.compile(r"^\(?\d{1,3}(,\d{3})*\)?$")
PAGE_FURNITURE = re.compile(r"^(Public Accounts of Canada \d{4}|Section \d+—|Transfer payments(—continued|—concluded)?$|\(in dollars\)$|"
                            r"This page has been intentionally left blank)")
DASH_FOOTNOTE = re.compile(r"^–\d$")
SECTION_NAME = re.compile(r"Section \d+—(.+?)(?: \d+ Public Accounts.*)?$")
MAX_EXTRA_PAGES = 6  # a section's table may run past its listed last page; read on until "Total Ministry"
FIELDS = ["doc_id", "section", "segment", "organization", "transfer_type", "label", "row_kind", "statutory",
          "used_current_year", "used_previous_year", "page"]


def amount(text: str) -> float:
    """Parse an amount, dropping a footnote digit glued to the end ('7,988,223,2285' -> 7,988,223,228)."""
    t = text.strip()
    core = t.strip("()")
    if t not in ("–", "-") and not GROUPED.match(t) and GROUPED.match(core[:-1]):
        t = ("(" if t.startswith("(") else "") + core[:-1] + (")" if t.endswith(")") else "")
    v = parse_amount(t)
    if v is None:
        raise ValueError(f"not an amount: {text!r}")
    return v


def read_section(pdf, sec: dict, doc_id: str, ncols: int) -> list[dict]:
    rows, pending = [], []
    org, ttype = "", ""
    first, last = sec["pages"]
    for n in range(first, min(last + MAX_EXTRA_PAGES, len(pdf.pages)) + 1):
        lines = page_lines(pdf.pages[n - 1])
        for ln in lines:  # a dash with a glued footnote digit ('–1') is nil
            for w in ln:
                if DASH_FOOTNOTE.match(w["text"]):
                    w["text"] = "–"
        texts = [" ".join(w["text"] for w in ln) for ln in lines]
        page_section = next((m.group(1) for t in texts if (m := SECTION_NAME.search(t))), None)
        if page_section and page_section != sec["section"]:
            break  # ran into another ministry's pages
        start = next((i for i, t in enumerate(texts) if t.startswith("Description previous years")), None)
        if start is None:
            if n == first or not rows:
                continue
            start = -1  # continuation page without the column header: read from the top
        for ln in lines[start + 1:]:
            label, amounts = split_line(ln)
            if len(amounts) < ncols:
                text = " ".join(w["text"] for w in ln).strip()
                if PAGE_FURNITURE.search(text):
                    continue
                if text in TYPES:
                    if pending:
                        org = " ".join(pending)
                    ttype, pending = TYPES[text], []
                elif text.startswith("(S) Statutory") or not text:
                    continue
                else:
                    pending.append(text)
                continue
            amounts = amounts[-ncols:]
            full = " ".join(pending + [label]).replace("…", "").strip(" .")
            full = re.sub(r"\s*\.{2,}\s*$", "", full).strip()
            pending = []
            kind = "total" if full.startswith("Total") else "detail"
            rows.append({"doc_id": doc_id, "section": sec["section"], "segment": sec["segment"], "organization": org,
                         "transfer_type": ttype if kind == "detail" else "", "label": full, "row_kind": kind,
                         "statutory": full.startswith("(S)"), "used_current_year": amount(amounts[5]["text"]),
                         "used_previous_year": amount(amounts[8]["text"]), "page": n})
            if full.startswith("Total Ministry"):
                return rows
    raise ValueError(f"{sec['section']}: no 'Total Ministry' line in pages {first}-{last}")


def main() -> int:
    manifest = load_manifest()
    ok = True
    for spec_path in sorted((CONFIG / "extraction" / "program-tables").glob("*.yaml")):
        spec = yaml.safe_load(spec_path.read_text())
        doc = manifest_doc(spec["doc_id"], manifest)
        out_dir = SILVER / "public-accounts" / spec["doc_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        rows, checks = [], []
        with pdfplumber.open(str(doc_path(doc))) as pdf:
            for sec in spec["sections"]:
                try:
                    srows = read_section(pdf, sec, spec["doc_id"], spec["columns_per_line"])
                except ValueError as e:
                    print(f"ERROR {e}")
                    ok = False
                    continue
                detail = sum(r["used_current_year"] for r in srows if r["row_kind"] == "detail")
                stated = next(r["used_current_year"] for r in srows if r["label"].startswith("Total Ministry"))
                passed = abs(detail - stated) < 2
                ok = ok and passed
                checks.append({"section": sec["section"], "programs": sum(r["row_kind"] == "detail" for r in srows),
                               "computed": detail, "stated": stated, "diff": detail - stated, "ok": passed})
                if not passed:
                    print(f"FAIL  {sec['section']}: programs add to {detail:,.0f}, Total Ministry is {stated:,.0f}")
                rows += srows
        with (out_dir / "transfer-payments.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        with (out_dir / "checks.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["section", "programs", "computed", "stated", "diff", "ok"])
            w.writeheader()
            w.writerows(checks)
        (out_dir / "lineage.json").write_text(json.dumps({
            "doc_id": spec["doc_id"], "source_file": rel(doc_path(doc)), "source_sha256": doc["file"].get("sha256"),
            "spec_file": rel(spec_path), "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
            "method": "pdfplumber_words (vol2 transfer tables)"}, indent=2) + "\n")
        n_ok = sum(c["ok"] for c in checks)
        print(f"{spec['doc_id']}: {sum(r['row_kind'] == 'detail' for r in rows)} programs, {n_ok}/{len(checks)} sections "
              f"tie to Total Ministry -> {rel(out_dir / 'transfer-payments.csv')}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
