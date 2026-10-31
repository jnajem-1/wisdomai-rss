#!/usr/bin/env python3
"""Build a comprehensive RSS 2.0 feed of all wisdom.ai/blog posts.
Sitemap-driven (Framer site; sitemap lists every post); per-post JSON-LD -> RSS.
Stdlib only. Writes docs/feed.xml next to this script (or --out PATH)."""
import os, re, sys, json, time, urllib.request
import xml.sax.saxutils as sx
from email.utils import format_datetime
from datetime import datetime, timezone

SITEMAP = "https://www.wisdom.ai/sitemap.xml"
SELF_URL = "https://jnajem-1.github.io/wisdomai-rss/feed.xml"
UA = "Mozilla/5.0 (compatible; wisdomai-rss/1.0; +https://github.com/jnajem-1/wisdomai-rss)"

def out_path():
    if "--out" in sys.argv:
        return sys.argv[sys.argv.index("--out")+1]
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "feed.xml")

def get(url, t=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return r.read().decode("utf-8", "replace")

def post_urls():
    s = get(SITEMAP, 30)
    found = re.findall(r"<loc>\s*(https://www\.wisdom\.ai/blog/[^<\s]+)\s*</loc>", s)
    out = []
    for u in found:
        u = u.strip()
        if u.rstrip("/") == "https://www.wisdom.ai/blog":
            continue
        if u not in out:
            out.append(u)
    return out

def meta(h, prop):
    return re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]+content=["\'](.*?)["\']' % re.escape(prop), h, re.I)

def jsonld_article(h):
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.S|re.I):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        items = list(data) if isinstance(data, list) else [data]
        for d in items:
            if isinstance(d, dict) and isinstance(d.get("@graph"), list):
                items.extend(d["@graph"])
        for d in items:
            if isinstance(d, dict) and "datePublished" in d and ("headline" in d or "description" in d or "image" in d or "name" in d):
                return d
    return {}

def clean_title(h, ld):
    t = ld.get("headline")
    if not t:
        mt = meta(h, "og:title"); t = mt.group(1) if mt else ""
    if not t:
        mt = re.search(r"<title>(.*?)</title>", h, re.S); t = mt.group(1) if mt else ""
    return re.sub(r"\s*\|\s*WisdomAI.*$", "", t or "", flags=re.I).strip()

def parse_post(url):
    h = get(url, 35)
    ld = jsonld_article(h)
    title = clean_title(h, ld)
    desc = ld.get("description") or (meta(h, "og:description").group(1) if meta(h, "og:description") else "")
    img = ld.get("image")
    if isinstance(img, dict): img = img.get("url")
    if isinstance(img, list) and img:
        img = img[0].get("url") if isinstance(img[0], dict) else img[0]
    if not img:
        mi = meta(h, "og:image"); img = mi.group(1) if mi else None
    if img: img = img.replace("&amp;", "&")
    pub = ld.get("datePublished") or (meta(h, "article:published_time").group(1) if meta(h, "article:published_time") else "")
    return {"link": url, "title": title, "desc": desc, "image": img, "pub": pub}

def to_rfc822(iso):
    s = (iso or "").strip().replace("Z", "+00:00")
    if not s: return ""
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt.astimezone(timezone.utc))
    except Exception:
        return ""

def xmltxt(s): return sx.escape(s or "")
def xmlattr(s): return sx.quoteattr(s or "")

def build():
    urls = post_urls()
    posts, errs = [], 0
    for u in urls:
        try:
            posts.append(parse_post(u))
        except Exception as e:
            errs += 1; sys.stderr.write("warn: %s -> %s\n" % (u, e))
        time.sleep(0.2)
    posts.sort(key=lambda p: p["pub"] or "", reverse=True)
    now = format_datetime(datetime.now(timezone.utc))
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">',
         '<channel>',
         '  <title>WisdomAI Blog</title>',
         '  <link>https://www.wisdom.ai/blog</link>',
         '  <atom:link href="%s" rel="self" type="application/rss+xml"/>' % SELF_URL,
         '  <description>Comprehensive feed of all WisdomAI blog posts (%d items).</description>' % len(posts),
         '  <language>en-us</language>',
         '  <lastBuildDate>%s</lastBuildDate>' % now,
         '  <ttl>60</ttl>',
         '  <generator>wisdomai_feed.py</generator>']
    for p in posts:
        L.append('  <item>')
        L.append('    <title>%s</title>' % xmltxt(p["title"]))
        L.append('    <link>%s</link>' % xmltxt(p["link"]))
        L.append('    <guid isPermaLink="true">%s</guid>' % xmltxt(p["link"]))
        if p["pub"]:
            L.append('    <pubDate>%s</pubDate>' % to_rfc822(p["pub"]))
        if p["desc"]:
            L.append('    <description>%s</description>' % xmltxt(p["desc"]))
        if p["image"]:
            L.append('    <media:content url=%s medium="image"/>' % xmlattr(p["image"]))
        L.append('  </item>')
    L += ['</channel>', '</rss>']
    out = out_path()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return len(posts), errs, out

if __name__ == "__main__":
    n, errs, out = build()
    print("posts=%d errors=%d out=%s" % (n, errs, out))
