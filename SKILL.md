---
name: amazon-store-exporter
description: Export every product listing from an Amazon seller/store/search URL into one folder per product, download the product gallery images, and create a Word document containing the title, bullet points, product description, ASIN, and source URL. Use for Amazon store catalog downloads, seller inventory archiving, listing-copy extraction, bulk Amazon product image downloads, or requests in Arabic or English to save all products from any amazon.ae, amazon.sa, amazon.com, or other Amazon marketplace store link.
---

# Amazon Store Exporter

Export a complete Amazon seller catalog into organized local folders. Use the signed-in browser when available, preserve the source language exactly, and do not attempt to bypass CAPTCHAs or access controls.

## Inputs and defaults

- Require one Amazon store, seller, storefront, brand-store, or search-results URL.
- Accept an optional output directory. If absent, create `outputs/amazon-store-export-YYYYMMDD-HHMM` in the current workspace.
- Treat every distinct ASIN as one product. Deduplicate variants or repeated search results by ASIN; if ASIN is unavailable, deduplicate by canonical product URL.
- Export all result pages unless the user specifies a limit.

## Workflow

1. Select the browser appropriate for the supplied URL and read its complete browser documentation before interaction.
2. Open the supplied URL. If Amazon presents a CAPTCHA, sign-in wall, robot check, or region-choice dialog that cannot be resolved normally, ask the user to complete it in the browser and continue afterward. Never bypass it.
3. Collect product detail URLs from the current results page. Prefer canonical `/dp/ASIN` links and remove tracking query parameters.
4. Continue through pagination until no enabled Next control remains. Also handle infinite-scroll result pages by scrolling until no new ASIN appears after two checks.
5. Maintain a set of discovered ASINs and URLs so sponsored, repeated, or variant cards are not exported twice.
6. Open each product detail page sequentially and extract:
   - `asin`
   - `title`
   - `bullet_points` as an ordered array, excluding empty rows and obvious promotional widgets
   - `description`, preferring the Product Description/A+ descriptive text; do not mistake technical tables, reviews, recommendations, or shipping text for the description
   - `source_url` as a canonical product URL
   - `image_urls` from the product gallery, preferring original/high-resolution URLs from page data over thumbnails
7. Preserve text verbatim and in its original language. Do not translate, rewrite, summarize, or invent missing fields. Use an empty string/list when a field is genuinely absent.
8. Save one JSON record per product temporarily, then run:

   `python <skill-dir>/scripts/export_product.py --input <record.json> --output <export-root>`

9. Record each product as `exported`, `skipped`, or `failed` in `<export-root>/export-summary.csv`. Continue after isolated product errors. Include ASIN, title, URL, status, and a short error.
10. At completion, report the export root, discovered/exported/failed counts, and failed ASINs. Provide a clickable link to the user-facing export directory when it is within the workspace outputs directory.

## Extraction guidance

- Use live DOM inspection first. Amazon selectors vary by locale and experiment; locate fields semantically and use several selector candidates instead of relying on one brittle selector.
- Typical title nodes include `#productTitle`.
- Typical bullet containers include `#feature-bullets` and feature lists near the title.
- Typical description sources include `#productDescription`, `#aplus`, and labeled Product Description sections. Preserve readable paragraph order.
- Gallery data may appear in image elements, `data-a-dynamic-image`, `data-old-hires`, `hiRes`, or page-embedded JSON. Deduplicate normalized URLs and exclude icons, videos, swatches, and recommendation images.
- Do not download customer-review images or images from related/sponsored products.
- If a product is unavailable but its page still exposes listing content, export the available fields and note the condition in the summary.

## Output contract

Create this structure:

```text
amazon-store-export-YYYYMMDD-HHMM/
  export-summary.csv
  ASIN - Safe Product Title/
    01.jpg
    02.jpg
    ...
    product-details.docx
    product-data.json
```

Sanitize folder names for the operating system, collapse whitespace, cap the title portion to 100 characters, and keep the ASIN at the start. Never overwrite another ASIN's folder. The bundled script performs this normalization and writes the Word file.

## Quality checks

- Confirm the number of unique product URLs collected across all pages.
- For a small catalog, compare the export folders to every discovered ASIN. For a large catalog, compare counts and spot-check the first, middle, and last exported products.
- Open at least one generated Word file and verify that title, bullets, description, and source URL are readable.
- Verify downloaded files are actual images and not HTML challenge pages; the script rejects non-image responses.
- Never claim completeness when pagination was blocked or interrupted. State the last completed page and partial counts.
