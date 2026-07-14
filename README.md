# Amazon Store Exporter

Codex skill for exporting Amazon seller/store/search listings into organized local folders.

Given an Amazon store URL, the skill:

- collects product detail pages across result pages
- deduplicates products by ASIN
- downloads product gallery images
- creates one folder per product
- writes `product-details.docx` with title, bullet points, description, ASIN, and source URL
- writes `product-data.json` for structured reuse
- writes `export-summary.csv` for the full export run

## Install

Copy this folder into your Codex skills directory:

```text
%USERPROFILE%\.codex\skills\amazon-store-exporter
```

Restart Codex if the skill does not appear immediately.

## Use

Ask Codex:

```text
Use $amazon-store-exporter to export every product from this Amazon store URL:
https://www.amazon.ae/s?me=A1ODH0W5WVZN4X&marketplaceID=A2VIGQ35RCS4UG
```

## Notes

- The skill does not bypass Amazon CAPTCHA, sign-in walls, robot checks, or access controls.
- If Amazon asks for verification, complete it in the browser and then continue.
- The export preserves the original listing language and does not translate or rewrite listing text.
