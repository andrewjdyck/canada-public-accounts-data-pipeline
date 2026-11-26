"""
Download source documents listed in data/1_bronze/source-docs-manifest.yaml and verify them.

Download methods (`download.method` in the manifest):
  script       download `source.url` (a PDF) to `data/1_bronze/<storage.relpath>` if missing.
  statcan_wds  download a Statistics Canada full-table CSV zip through the Web Data
               Service (`source.statcan_product_id`), if missing. With --refresh, also
               re-download when StatCan has published a newer release than the one recorded.
  manual       never downloaded (e.g. the host blocks scripts); only verified if present.

For every file present:
  - compute sha256 and byte size;
  - if the manifest records a sha256, fail on mismatch (the publisher changed the file,
    or the download is wrong);
  - with --record, write sha256/bytes/retrieved_at (and StatCan release_time) back into
    the manifest for documents that don't have them yet, or that were refreshed.

The manifest is validated against its JSON schema before anything is downloaded.

Requires: requests, PyYAML, jsonschema, truststore (uses the OS certificate store;
several Canadian government hosts don't validate against certifi's bundle).

Usage:
  python src/fetch/fetch_sources.py                       # download missing + verify
  python src/fetch/fetch_sources.py --record              # also write hashes into the manifest
  python src/fetch/fetch_sources.py --only statcan-cofog-by-component --refresh --record
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import MANIFEST, doc_path, load_manifest, rel  # noqa: E402

# Browser-like UA: open.alberta.ca returns 500 for non-browser user agents.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
WDS = "https://www150.statcan.gc.ca/t1/wds/rest"
MAGIC = {"pdf": b"%PDF-", "zip": b"PK\x03\x04"}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, fmt: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=300) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    magic = MAGIC.get(fmt)
    with tmp.open("rb") as f:
        if magic and f.read(len(magic)) != magic:
            tmp.unlink()
            raise RuntimeError(f"downloaded file is not a {fmt} (bad header)")
    tmp.replace(dest)


def statcan_release_time(product_id: str) -> str:
    r = requests.post(f"{WDS}/getCubeMetadata", json=[{"productId": int(product_id)}], timeout=60)
    r.raise_for_status()
    return r.json()[0]["object"]["releaseTime"]


def statcan_download_url(product_id: str) -> str:
    r = requests.get(f"{WDS}/getFullTableDownloadCSV/{product_id}/en", timeout=60)
    r.raise_for_status()
    body = r.json()
    if body.get("status") != "SUCCESS":
        raise RuntimeError(f"WDS getFullTableDownloadCSV failed: {body}")
    return body["object"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", action="store_true", help="Write sha256/bytes/retrieved_at into the manifest")
    parser.add_argument("--refresh", action="store_true", help="Re-download StatCan tables that have a newer release")
    parser.add_argument("--only", action="append", default=[], help="Limit to these document ids (repeatable)")
    args = parser.parse_args()

    manifest = load_manifest()
    today = dt.date.today().isoformat()
    failures = 0
    changed = False

    for doc in manifest["documents"]:
        doc_id = doc["id"]
        if args.only and doc_id not in args.only:
            continue
        method = doc.get("download", {}).get("method", "manual")
        path = doc_path(doc)
        file_meta = doc.setdefault("file", {})
        fmt = file_meta.get("format", "pdf")
        fetched = False

        try:
            if method == "statcan_wds":
                pid = doc["source"]["statcan_product_id"]
                latest = statcan_release_time(pid)
                recorded_release = doc["source"].get("release_time")
                newer = recorded_release is not None and latest > recorded_release
                if newer and not args.refresh:
                    print(f"NOTE   {doc_id}: StatCan release {latest} is newer than recorded {recorded_release} "
                          "(rerun with --refresh --record to update)")
                if not path.exists() or (newer and args.refresh):
                    url = statcan_download_url(pid)
                    print(f"GET    {doc_id}: {url} (release {latest})")
                    download(url, path, fmt)
                    fetched = True
                    if newer:  # a new vintage replaces the old hash rather than failing on it
                        file_meta.pop("sha256", None)
                        file_meta.pop("bytes", None)
                    if args.record:
                        doc["source"]["url"] = url
                        doc["source"]["release_time"] = latest
            elif not path.exists():
                if method != "script":
                    print(f"SKIP   {doc_id}: manual download required -> {rel(path)}")
                    continue
                print(f"GET    {doc_id}: {doc['source']['url']}")
                download(doc["source"]["url"], path, fmt)
                fetched = True
        except Exception as e:  # report and keep going
            print(f"FAIL   {doc_id}: {e}")
            failures += 1
            continue

        if fetched and args.record:
            doc["source"]["retrieved_at"] = today
            changed = True

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
        print(f"wrote {rel(MANIFEST)}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
