"""
Download source documents listed in source-docs/manifest.yaml and verify them.

For every document with `download.method: script`:
  - download `source.url` to `source-docs/<storage.relpath>` if the file is missing;
  - compute sha256 and byte size;
  - if the manifest already records a sha256, fail on mismatch (the publisher
    changed the file, or the download is wrong);
  - with --record, write sha256/bytes/retrieved_at back into the manifest for
    documents that don't have them yet.

Documents with `download.method: manual` are only verified if the file exists.

Requires: requests, PyYAML, truststore (uses the OS certificate store; several
Canadian government hosts don't validate against certifi's bundle).

Usage:
  python src/pa_pdf/fetch_sources.py                 # download missing + verify
  python src/pa_pdf/fetch_sources.py --record        # also write hashes into the manifest
  python src/pa_pdf/fetch_sources.py --only prov-on-public-accounts-2025-26
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path

import truststore

truststore.inject_into_ssl()

import requests  # noqa: E402  (must come after truststore injection)
import yaml  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO / "source-docs"
MANIFEST = SOURCE_DIR / "manifest.yaml"
# Browser-like UA: open.alberta.ca returns 500 for non-browser user agents.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=120) as r:
        r.raise_for_status()
        ctype = r.headers.get("content-type", "")
        if "pdf" not in ctype and not url.lower().endswith(".pdf"):
            raise RuntimeError(f"expected a PDF, got content-type {ctype!r}")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    with tmp.open("rb") as f:
        if f.read(5) != b"%PDF-":
            tmp.unlink()
            raise RuntimeError("downloaded file is not a PDF (missing %PDF- header)")
    tmp.replace(dest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", action="store_true", help="Write sha256/bytes/retrieved_at into the manifest")
    parser.add_argument("--only", action="append", default=[], help="Limit to these document ids (repeatable)")
    args = parser.parse_args()

    manifest = yaml.safe_load(MANIFEST.read_text())
    today = dt.date.today().isoformat()
    failures = 0
    changed = False

    for doc in manifest["documents"]:
        doc_id = doc["id"]
        if args.only and doc_id not in args.only:
            continue
        method = doc.get("download", {}).get("method", "manual")
        path = SOURCE_DIR / doc["storage"]["relpath"]
        file_meta = doc.setdefault("file", {})

        if not path.exists():
            if method != "script":
                print(f"SKIP   {doc_id}: manual download required -> {path.relative_to(REPO)}")
                continue
            print(f"GET    {doc_id}: {doc['source']['url']}")
            try:
                download(doc["source"]["url"], path)
            except Exception as e:  # report and keep going
                print(f"FAIL   {doc_id}: {e}")
                failures += 1
                continue
            if args.record:
                doc["source"]["retrieved_at"] = today

        digest = sha256_of(path)
        size = path.stat().st_size
        recorded = file_meta.get("sha256")
        if recorded and recorded != digest:
            print(f"FAIL   {doc_id}: sha256 mismatch (manifest {recorded[:12]}…, file {digest[:12]}…)")
            failures += 1
            continue
        if not recorded and args.record:
            file_meta["sha256"] = digest
            file_meta["bytes"] = size
            if doc.get("status") in (None, "planned"):
                doc["status"] = "downloaded"
            changed = True
        state = "ok" if recorded else ("recorded" if args.record else "unrecorded")
        print(f"OK     {doc_id}: {size:,} bytes sha256={digest[:12]}… ({state})")

    if changed:
        manifest["updated_at"] = today
        MANIFEST.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=120))
        print(f"wrote {MANIFEST.relative_to(REPO)}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
