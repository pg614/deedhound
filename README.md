# Ohio Sheriff Sale Tracker (prototype, not deployed)
- county_sources.csv — 88-county survey
- scraper/official.py [county...] — sheriff-published lists only (robots-checked); writes data/<county>.json (2s delay between requests)
- build.py — generates static site in site/ (SITE_URL env sets canonical/sitemap base)
- Run locally: python3 build.py && cd site && python3 -m http.server 8765
- .github/workflows/daily.yml — daily refresh + GitHub Pages deploy (inactive until a repo exists)
CAUTION: sheriffsaleauction.ohio.gov robots.txt = "Disallow: /". Get permission from RealAuction/Ohio DAS before running this scraper in production.
