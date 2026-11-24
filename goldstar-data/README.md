# goldstar-data

Daily Ghana Stock Exchange price snapshots used by the GoldStar app.

- `data/latest.json` - latest prices and company details for every listed stock
- `data/history/<TICKER>.json` - one row per trading day: `d` date, `p` price, `c` change, `v` volume
- `scripts/snapshot.py` - the script that fetches the prices
- `.github/workflows/snapshot.yml` - runs the script every weekday at 16:00 UTC

Prices come from the community feed at https://dev.kwayisi.org/apis/gse. For information only, not investment advice.
