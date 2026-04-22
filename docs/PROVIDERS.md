# Lookup Providers — open-inventory

Reference for the built-in product lookup chain and guide for adding new
providers.

---

## How the Chain Works

On first scan of an unknown GTIN the `ChainRunner` (`inv/lookup/chain.py`)
tries each provider in priority order.  It stops at the first hit and
writes the result through to `product_cache` (SQLite).  All subsequent
scans of the same GTIN are served from cache — no network call is made.

```
GTIN →  0: ProductCache (local SQLite)     always checked first
         1: Open Food Facts                 food & consumables
         2: Open Library                    ISBN-10/13 books/media
         3: OpenGTINdb                      general goods (stub — always misses in V1)
         4: UPCitemdb (free tier)           broad consumer goods, rate-limited
         ─ all miss → create needs_review stub
```

---

## Built-in Providers

### 0 · Local Cache (`inv/lookup/cache.py`)

Always consulted first.  If the GTIN was seen before, the cached
`ProviderResult` is returned immediately with no network activity.

### 1 · Open Food Facts (`inv/lookup/openfoodfacts.py`)

- **Coverage:** food, beverage, and household consumables with EAN/GTIN barcodes
- **Auth:** none
- **Endpoint:** `https://world.openfoodfacts.org/api/v2/product/<gtin>.json`
- **Timeout:** 3 s
- **Notes:** Best coverage for food items sold in Europe and North America.

### 2 · Open Library (`inv/lookup/openlibrary.py`)

- **Coverage:** books and media identified by ISBN-10 / ISBN-13
- **Auth:** none
- **Endpoint:** `https://openlibrary.org/api/books?bibkeys=ISBN:<isbn>&format=json&jscmd=data`
- **Timeout:** 3 s
- **Notes:** Only activated for GTINs that look like ISBN-13 (978/979 prefix).

### 3 · OpenGTINdb (`inv/lookup/opengtindb.py`)

- **Coverage:** community GTIN database
- **Status in V1:** stub — the API returns HTML rather than JSON; always misses.  Slot reserved for V2.

### 4 · UPCitemdb free tier (`inv/lookup/upcitemdb.py`)

- **Coverage:** broad US consumer goods with UPC-A barcodes
- **Auth:** none (IP-based rate limit: ~100 lookups/day)
- **Endpoint:** `https://api.upcitemdb.com/prod/trial/lookup?upc=<upc>`
- **Timeout:** 3 s
- **Notes:** Only accepts 12-digit UPC-A.  13-digit EAN-13 with a leading
  zero is stripped to 12 digits and tried.  All other lengths are skipped.
  HTTP 429 (rate limit) is logged as a warning rather than silently
  treated as a miss so operators can see when the daily quota is exhausted.

---

## Adding a New Provider

1. **Create the module** in `inv/lookup/`.  The filename should match the
   service name (e.g. `inv/lookup/myservice.py`).

2. **Implement the protocol:**

   ```python
   # inv/lookup/myservice.py
   from __future__ import annotations
   import httpx
   from inv.lookup.base import ProviderResult

   class MyServiceProvider:
       name = "myservice"  # stable identifier — used in cache + events

       async def lookup(self, gtin: str) -> ProviderResult | None:
           try:
               async with httpx.AsyncClient(timeout=3.0) as client:
                   resp = await client.get(
                       "https://api.myservice.example/lookup",
                       params={"upc": gtin},
                   )
                   resp.raise_for_status()
                   data = resp.json()
           except Exception:
               return None  # never propagate — chain must continue

           if not data.get("found"):
               return None

           return ProviderResult(
               gtin=gtin,
               provider=self.name,
               name=data.get("title"),
               brand=data.get("brand"),
               raw=data,
           )
   ```

3. **Register it in `chain.py`:**

   ```python
   # inv/lookup/chain.py — add to the providers list
   from inv.lookup.myservice import MyServiceProvider

   _PROVIDERS: list[ProductLookupProvider] = [
       CacheProvider(cache_repo),
       OpenFoodFactsProvider(),
       OpenLibraryProvider(),
       OpenGTINdbProvider(),
       UPCitemdbProvider(),
       MyServiceProvider(),   # ← add here
   ]
   ```

4. **Write a test** in `tests/unit/` mocking the HTTP response with `respx`.

5. **Add a fixture** in `tests/fixtures/providers/myservice_hit.json` with
   a representative API response.

---

## Provider Contract

- **Return `None`** on any miss (GTIN not found) or any error.
- **Never propagate exceptions** — the chain must continue to the next
  provider even if one throws.
- **Respect timeouts** — use `httpx.AsyncClient(timeout=3.0)`.
- **`name` must be stable** — it is written to `product_cache.provider`
  and appears in `ItemEnrichedEvent.provider`.  Renaming is a breaking
  change for existing caches.
