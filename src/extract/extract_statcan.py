"""
Extract StatCan full-table CSVs from their bronze zips into silver.

For every manifest document with `download.method: statcan_wds`, read the data CSV
inside the zip (without unpacking it to disk) and write
data/2_silver/statcan/<product_id>.csv with the columns needed downstream, labels kept
exactly as StatCan prints them (including the CCOFOG codes in square brackets).
Nothing is categorised or filtered here except dropping StatCan's technical columns.

Usage:
  python src/extract/extract_statcan.py
"""

from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import SILVER, doc_path, load_manifest, rel  # noqa: E402

KEEP = ["REF_DATE", "GEO", "Public sector components", "UOM", "SCALAR_FACTOR", "VECTOR", "COORDINATE",
        "VALUE", "STATUS", "SYMBOL", "TERMINATED"]


def main() -> int:
    manifest = load_manifest()
    out_dir = SILVER / "statcan"
    out_dir.mkdir(parents=True, exist_ok=True)
    for doc in manifest["documents"]:
        if doc.get("download", {}).get("method") != "statcan_wds":
            continue
        pid = doc["source"]["statcan_product_id"]
        zpath = doc_path(doc)
        if not zpath.exists():
            print(f"SKIP {doc['id']}: {rel(zpath)} missing (run src/fetch/fetch_sources.py)")
            continue
        with zipfile.ZipFile(zpath) as z:
            with z.open(f"{pid}.csv") as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"))
                # The classification column is named after the table's last dimension.
                dims = [c for c in reader.fieldnames if c not in KEEP and c not in
                        ("DGUID", "UOM_ID", "SCALAR_ID", "DECIMALS")]
                fields = ["doc_id", "REF_DATE", "GEO", "Public sector components", *[d for d in dims if d != "Public sector components"],
                          "UOM", "SCALAR_FACTOR", "VALUE", "STATUS", "SYMBOL", "TERMINATED", "VECTOR", "COORDINATE"]
                out = out_dir / f"{pid}.csv"
                n = 0
                with out.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                    w.writeheader()
                    for row in reader:
                        row["doc_id"] = doc["id"]
                        w.writerow(row)
                        n += 1
        (out_dir / f"{pid}.lineage.json").write_text(json.dumps({
            "doc_id": doc["id"], "source_file": rel(zpath), "source_sha256": doc["file"].get("sha256"),
            "statcan_release_time": doc["source"].get("release_time"), "rows": n}, indent=2) + "\n")
        print(f"OK   {doc['id']}: {n:,} rows -> {rel(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
