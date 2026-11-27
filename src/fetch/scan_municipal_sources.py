"""
Scan city websites for annual financial reports and record where they are.

Reads config/municipal/cities.yaml. For each city:
  1. fetches each landing page and keeps PDF links whose text or URL looks like an annual
     report, financial statements, public accounts or SOFI (include/exclude patterns);
  2. probes URL templates ({year} filled in for recent years) for files that exist;
  3. checks the known documents listed in the config.
Every candidate is checked with an HTTP HEAD (status, content type, size, last modified); it counts as
verified only if the server returns a PDF (some sites answer 200 with an HTML page for missing files).

Writes data/1_bronze/municipal/source-scan.yaml: one entry per city with its candidates
(kind, year, url, link text, how it was found, HTTP check) and any errors (e.g. a host this
network does not allow). Nothing is downloaded.

With --update-manifest, each verified document from a city's newest reporting year is added to
data/1_bronze/source-docs-manifest.yaml as a `planned` document (download.method: script),
so `fetch_sources.py` can download it. Existing ids and URLs are left alone.

Usage:
  python src/fetch/scan_municipal_sources.py
  python src/fetch/scan_municipal_sources.py --only regina-sk --update-manifest
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import truststore

truststore.inject_into_ssl()

import requests  # noqa: E402
import yaml  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import BRONZE, CONFIG, MANIFEST, load_manifest, rel  # noqa: E402

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
              "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
KIND_PATTERNS = [  # first match wins
    ("sofi", re.compile(r"statement of financial information|\bsofi\b", re.I)),
    ("public_accounts", re.compile(r"public accounts", re.I)),
    ("financial_statement", re.compile(r"financial statements?|finstat", re.I)),
    ("annual_report", re.compile(r"annual (financial )?report|financial report|annualreport", re.I)),
]
MANIFEST_KIND = {"annual_report": "annual_report", "financial_statement": "financial_statement",
                 "public_accounts": "public_accounts", "sofi": "financial_statement"}
YEAR = re.compile(r"(?<!\d)(199\d|20[0-3]\d)(?!\d)")
SCAN_FILE = BRONZE / "municipal" / "source-scan.yaml"


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(" ".join(self._text).split())))
            self._href = None


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-CA,en;q=0.9",
                      "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8"})
    return s


def head(s: requests.Session, url: str) -> dict:
    try:
        r = s.head(url, allow_redirects=True, timeout=45)
        if r.status_code in (403, 405):  # some servers refuse HEAD; ask for one byte instead
            r = s.get(url, allow_redirects=True, timeout=45, stream=True, headers={"Range": "bytes=0-0"})
            r.close()
        size = r.headers.get("content-length")
        if r.status_code == 206 and "content-range" in r.headers:
            size = r.headers["content-range"].rsplit("/", 1)[-1]
        return {"status": r.status_code, "final_url": r.url if r.url != url else None,
                "content_type": r.headers.get("content-type", "").split(";")[0] or None,
                "bytes": int(size) if size and size.isdigit() else None,
                "last_modified": r.headers.get("last-modified")}
    except requests.RequestException as e:
        return {"status": None, "error": short_error(e)}


def short_error(e: Exception) -> str:
    text = str(e)
    if "403" in text and "Tunnel" in text:
        return "host not allowed by this network (proxy 403)"
    return text[:200]


def kind_of(text: str) -> str | None:
    return next((k for k, rx in KIND_PATTERNS if rx.search(text)), None)


def year_of(text: str, url: str, today: dt.date) -> int | None:
    """Report year from the link text, else the file name; never the folder path (upload dates).
    A calendar-year report for year Y is published in Y+1, so years after last year are ignored."""
    for source in (text, unquote(Path(urlparse(url).path).name)):
        years = [int(y) for y in YEAR.findall(source) if int(y) <= today.year - 1]
        if years:
            return max(years)
    return None


def clean_url(url: str) -> str:
    """Drop cache-busting query strings (?cb=...) so the same file is listed once."""
    return url.split("?")[0] if re.search(r"\?(cb|v|ver)=\d+$", url) else url


def is_pdf(check: dict) -> bool:
    return check.get("status") in (200, 206) and "pdf" in (check.get("content_type") or "")


def scan_city(s: requests.Session, city: dict, defaults: dict, today: dt.date) -> dict:
    include = re.compile(city.get("include_link_pattern", defaults["include_link_pattern"]), re.I)
    exclude = re.compile(city.get("exclude_link_pattern", defaults["exclude_link_pattern"]), re.I)
    found: dict[str, dict] = {}
    errors = []

    def add(url, kind, year, how, text=""):
        if url in found:
            found[url]["found_via"] = sorted(set(found[url]["found_via"]) | {how})
            return
        found[url] = {"kind": kind, "year": year, "url": url, "link_text": text or None, "found_via": [how]}

    for page in city.get("landing_pages", []):
        try:
            r = s.get(page, timeout=60)
            r.raise_for_status()
        except requests.RequestException as e:
            errors.append({"url": page, "error": short_error(e)})
            continue
        parser = Links()
        parser.feed(r.text)
        for href, text in parser.links:
            if not href:
                continue
            url = clean_url(urljoin(r.url, href))
            label = f"{text} {unquote(urlparse(url).path)}"
            looks_like_doc = url.lower().split("?")[0].endswith(".pdf") or "/media/" in url
            if not looks_like_doc or not include.search(label) or exclude.search(label):
                continue
            add(url, kind_of(label) or "annual_report", year_of(text, url, today), f"landing_page: {page}", text)

    for t in city.get("url_templates", []):
        for year in range(today.year - 1, today.year - defaults["years_back"] - 1, -1):
            url = t["url"].format(year=year)
            check = head(s, url)
            if is_pdf(check):
                add(url, t["kind"], year, "url_template")
            elif check.get("error") and not any(e["url"] == url for e in errors):
                errors.append({"url": url, "error": check["error"]})
                break

    for d in city.get("known_documents", []):
        add(d["url"], d["kind"], d["year"], "known_document (web search)")

    for c in found.values():
        c["check"] = head(s, c["url"])
    candidates = sorted(found.values(), key=lambda c: (-(c["year"] or 0), c["kind"], c["url"]))
    for c in candidates:
        c["verified"] = is_pdf(c["check"])
    verified = [c for c in candidates if c["verified"]]
    return {"id": city["id"], "name": city["name"], "province": city["province"],
            "scanned_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "candidates": candidates, "verified": len(verified), "errors": errors,
            "notes": city.get("notes")}


def update_manifest(results: list[dict], today: dt.date) -> int:
    manifest = load_manifest()
    known_urls = {d["source"]["url"] for d in manifest["documents"]}
    known_ids = {d["id"] for d in manifest["documents"]}
    added = 0
    for city in results:
        latest: dict[str, dict] = {}
        verified_years = [c["year"] for c in city["candidates"] if c.get("verified") and c["year"]]
        if not verified_years:
            continue
        newest = max(verified_years)
        for c in city["candidates"]:
            # Only the city's newest reporting year: an older document of another kind is not useful.
            if not c.get("verified") or c["year"] != newest:
                continue
            if c["kind"] not in latest or c["year"] > latest[c["kind"]]["year"]:
                latest[c["kind"]] = c
        for kind, c in latest.items():
            slug = kind.replace("_", "-")
            doc_id = f"mun-{city['id']}-{slug}-{c['year']}"
            url = c["check"].get("final_url") or c["url"]
            if doc_id in known_ids or url in known_urls or c["url"] in known_urls:
                continue
            filename = unquote(Path(urlparse(url).path).name) or f"{doc_id}.pdf"
            manifest["documents"].append({
                "id": doc_id, "level": "municipal",
                "jurisdiction": {"country": "CA", "province": city["province"], "municipality": city["id"]},
                "entity": {"name": city["name"], "short": city["id"].split("-")[0], "type": "government"},
                "doc": {"kind": MANIFEST_KIND[kind], "title": c.get("link_text") or f"{city['name']} {c['year']} {kind.replace('_', ' ')}",
                        "fiscal_year": str(c["year"]), "period_covered": {"start": f"{c['year']}-01-01", "end": f"{c['year']}-12-31"},
                        "language": "en"},
                "source": {"url": url, "retrieved_at": today.isoformat(), "publisher": city["name"]},
                "download": {"method": "script"},
                "storage": {"relpath": f"municipal/{city['id']}/{filename}"},
                "file": {"format": "pdf"}, "status": "planned", "tags": ["municipal", kind],
                "notes": f"Found by src/fetch/scan_municipal_sources.py via {', '.join(c['found_via'])}.",
            })
            known_ids.add(doc_id)
            known_urls.add(url)
            added += 1
    if added:
        manifest["updated_at"] = today.isoformat()
        MANIFEST.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=120))
        load_manifest()  # re-validate against the schema
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", default=[], help="City id (repeatable)")
    parser.add_argument("--update-manifest", action="store_true", help="Add the latest verified documents as planned manifest entries")
    args = parser.parse_args()

    cfg = yaml.safe_load((CONFIG / "municipal" / "cities.yaml").read_text())
    today = dt.date.today()
    s = session()
    previous = yaml.safe_load(SCAN_FILE.read_text()) if SCAN_FILE.exists() else {"cities": []}
    results = {c["id"]: c for c in previous.get("cities", [])}
    for city in cfg["cities"]:
        if args.only and city["id"] not in args.only:
            continue
        r = scan_city(s, city, cfg["defaults"], today)
        results[city["id"]] = r
        latest = next((c for c in r["candidates"] if c["verified"]), None)
        print(f"{city['id']:14s} {len(r['candidates'])} candidates, {r['verified']} verified"
              + (f"; latest {latest['year']} {latest['kind']}" if latest else "")
              + (f"; {len(r['errors'])} errors ({r['errors'][0]['error']})" if r["errors"] else ""))
    SCAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCAN_FILE.write_text("# Generated by src/fetch/scan_municipal_sources.py; do not edit (config: config/municipal/cities.yaml).\n"
                         + yaml.safe_dump({"scan_version": 1, "cities": [results[c["id"]] for c in cfg["cities"] if c["id"] in results]},
                                          sort_keys=False, allow_unicode=True, width=140))
    print(f"wrote {rel(SCAN_FILE)}")
    if args.update_manifest:
        n = update_manifest(list(results.values()), today)
        print(f"added {n} planned documents to {rel(MANIFEST)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
