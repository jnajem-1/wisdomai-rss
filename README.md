# wisdomai-rss

Comprehensive RSS 2.0 feed of **all** posts on https://www.wisdom.ai/blog (past the site's client-side "Load More").

- **Feed URL:** https://jnajem-1.github.io/wisdomai-rss/feed.xml
- **How:** the site is a Framer app with no native RSS, but `sitemap.xml` lists every post and each post page embeds JSON-LD (headline/description/datePublished/image). This repo turns that into RSS.
- **Refresh:** a GitHub Action regenerates `docs/feed.xml` hourly (cron `17 * * * *`) and commits it; GitHub Pages serves it.
- **Run locally:** `python wisdomai_feed.py` (writes `docs/feed.xml`), or `python wisdomai_feed.py --out /path/feed.xml`.
- Inspired by https://github.com/Olshansk/rss-feeds, simplified to a sitemap-driven approach.
