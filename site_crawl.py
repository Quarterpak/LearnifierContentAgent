# site_crawl.py
import os, re, time, argparse
import requests
from urllib.parse import urlparse
from lxml import etree
import trafilatura

SITEMAP_URL = "https://www.learnifier.com/sitemap.xml"  # if it lives elsewhere, update
OUT_DIR = "data/site"  # will create /en and /sv inside

HEADERS = {"User-Agent": "LearnifierContentAgent/1.0 (+https://www.learnifier.com)"}

def slugify(url: str) -> str:
    """Turn a URL path into a safe filename."""
    path = urlparse(url).path.strip("/")
    if not path:
        return "home"
    # keep last two segments to avoid huge names
    parts = [p for p in path.split("/") if p]
    tail = "-".join(parts[-2:]) if len(parts) > 1 else parts[-1]
    return re.sub(r"[^a-zA-Z0-9\-]+", "-", tail) or "page"

def parse_sitemap(sitemap_url: str):
    r = requests.get(sitemap_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    root = etree.fromstring(r.content)
    ns = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "xhtml": "http://www.w3.org/1999/xhtml",
    }

    by_lang = {"en": set(), "sv": set()}
    for url in root.findall("sm:url", ns):
        # default loc
        loc = (url.findtext("sm:loc", namespaces=ns) or "").strip()
        if loc:
            by_lang["en"].add(loc)  # homepage often defaults to en

        for alt in url.findall("xhtml:link", ns):
            href = alt.get("href", "").strip()
            hreflang = (alt.get("hreflang", "") or "").lower()
            if not href or not hreflang:
                continue
            if hreflang.startswith("sv"):
                by_lang["sv"].add(href)
            elif hreflang.startswith("en") or hreflang == "x-default":
                by_lang["en"].add(href)

    return {k: sorted(v) for k, v in by_lang.items()}

def fetch_and_extract(url: str):
    html = trafilatura.fetch_url(url)
    if not html:
        print(f"     fetch failed: {url}")
        return None

    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=True,
        output_format="markdown",  # ✅ updated
        url=url,
    )

    # Avoid saving garbage
    if not text or len(text.strip()) < 300:
        print(f"     nothing meaningful extracted: {url}")
        return None

    return text


def save_markdown(md: str, url: str, lang: str):
    out_dir = os.path.join(OUT_DIR, lang)
    os.makedirs(out_dir, exist_ok=True)
    name = slugify(url) + ".md"
    path = os.path.join(out_dir, name)
    front_matter = f"---\nsource: {url}\nlanguage: {lang}\n---\n\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(front_matter + md)
    return path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["en", "sv"], default="en")
    parser.add_argument("--limit", type=int, default=0, help="limit number of pages (0 = no limit)")
    parser.add_argument("--delay", type=float, default=0.7, help="seconds between requests")
    parser.add_argument("--sitemap", default=SITEMAP_URL)
    args = parser.parse_args()

    url_lists = parse_sitemap(args.sitemap)
    urls = url_lists.get(args.language, [])
    if args.limit:
        urls = urls[: args.limit]

    print(f"🌐 Crawling {len(urls)} {args.language.upper()} pages from sitemap…")
    saved = 0
    for i, url in enumerate(urls, 1):
        try:
            md = fetch_and_extract(url)
            if not md or len(md.strip()) < 120:  # skip pages with almost no body
                print(f"   {i:>3}/{len(urls)} skipped (empty): {url}")
            else:
                path = save_markdown(md, url, args.language)
                saved += 1
                print(f"   {i:>3}/{len(urls)} saved -> {path}")
        except Exception as e:
            print(f"   {i:>3}/{len(urls)} error {e}: {url}")
        time.sleep(args.delay)

    print(f"✅ Done. Saved {saved}/{len(urls)} {args.language.upper()} pages to {OUT_DIR}/{args.language}")

if __name__ == "__main__":
    main()
