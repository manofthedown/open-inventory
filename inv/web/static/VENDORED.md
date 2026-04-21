# Vendored Frontend Assets

open-inventory ships its frontend dependencies **vendored locally** so the app runs
fully offline (DEVELOPMENT_PLAN.md §8 rule: no build step, no bundler, no Node).

When upgrading, download the file directly from the source URL below, drop it in
place, and update both the version and the SHA256 in the table. CI will refuse
any vendored file larger than 1 MB (`.pre-commit-config.yaml`:
`check-added-large-files`).

| File | Version | License | Source URL | SHA256 |
|------|---------|---------|------------|--------|
| `js/htmx.min.js` | 2.0.4 | BSD-2-Clause (© Big Sky Software) | https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js | `e209dda5c8235479f3166defc7750e1dbcd5a5c1808b7792fc2e6733768fb447` |
| `js/alpine.min.js` | 3.14.9 | MIT (© Caleb Porzio) | https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js | `3ed1eed252488921df65e363d6715deb04d7f92aaedb9e52199fdf73cb1e0ad3` |
| `css/pico.min.css` | 2.0.6 | MIT (© Pico CSS) | https://cdn.jsdelivr.net/npm/@picocss/pico@2.0.6/css/pico.min.css | `dd5fd5591afd81ee21dcc117ad85c014dc3f1f19dc2d7b7d101ea0acc29274c2` |

## Verifying

```bash
cd inv/web/static
sha256sum -c <<'SUMS'
e209dda5c8235479f3166defc7750e1dbcd5a5c1808b7792fc2e6733768fb447  js/htmx.min.js
3ed1eed252488921df65e363d6715deb04d7f92aaedb9e52199fdf73cb1e0ad3  js/alpine.min.js
dd5fd5591afd81ee21dcc117ad85c014dc3f1f19dc2d7b7d101ea0acc29274c2  css/pico.min.css
SUMS
```

## First-party files

| File | Purpose |
|------|---------|
| `js/scan_focus.js` | Keeps the scan input re-focused after HTMX partial swaps. MIT-licensed as part of open-inventory (AGPL-3.0-or-later as a derivative work when shipped with the server). |

## Licenses

- HTMX is BSD-2-Clause.
- Alpine.js is MIT.
- Pico.css is MIT.

All three permit redistribution in minified/bundled form with attribution.
Attribution headers are preserved in the minified files themselves.
