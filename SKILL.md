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
   - `image_urls` from the main product gallery only, preferring original/high-resolution URLs from page data over thumbnails
7. Preserve text verbatim and in its original language. Do not translate, rewrite, summarize, or invent missing fields. Use an empty string/list when a field is genuinely absent.
8. Save one JSON record per product temporarily, then run:

   `python <skill-dir>/scripts/export_product.py --input <record.json> --output <export-root>`

   Pass only product-level output roots to `--output`, never a product folder. The script creates exactly one product folder inside that root.

9. Record each product as `exported`, `skipped`, or `failed` in `<export-root>/export-summary.csv`. Continue after isolated product errors. Include ASIN, title, URL, status, and a short error.
10. At completion, report the export root, discovered/exported/failed counts, and failed ASINs. Provide a clickable link to the user-facing export directory when it is within the workspace outputs directory.

## Browser setup recovery

- If browser setup fails before Amazon opens with `Cannot redefine property: process`, treat it as a Codex/browser-control session issue, not an Amazon export issue.
- Do not start a partial export when this happens. Tell the user no products were collected yet.
- Ask the user to start a fresh Codex task or restart Codex, then rerun the same store URL.
- After restart, use the browser normally and continue from Workflow step 1.
- Never report that Amazon blocked the export unless the Amazon page itself displays a CAPTCHA, robot check, sign-in wall, or region-choice dialog.

## Extraction guidance

- Use live DOM inspection first. Amazon selectors vary by locale and experiment; locate fields semantically and use several selector candidates instead of relying on one brittle selector.
- Typical title nodes include `#productTitle`.
- Typical bullet containers include `#feature-bullets` and feature lists near the title.
- Typical description sources include `#productDescription`, `#aplus`, and labeled Product Description sections. Preserve readable paragraph order.
- Gallery data may appear in image elements, `data-a-dynamic-image`, `data-old-hires`, `hiRes`, `large`, or page-embedded JSON. Prefer these sources in order: embedded `colorImages.initial[].hiRes`, embedded `large`, `data-old-hires`, then the largest key in `data-a-dynamic-image`. Avoid using visible thumbnails as final image URLs.
- Normalize Amazon image URLs before saving. Strip sizing/transformation segments such as `._AC_SL1500_`, `._SX679_`, `._SS40_`, `._AC_US40_`, and similar marker blocks so the URL points to the base image file. This prevents downloading the same image in multiple sizes.
- Deduplicate gallery images by normalized base image identity, not by the raw URL string. The same image may appear as a thumbnail, hover image, and high-resolution image with different URLs. For Amazon media filenames, treat leading two-character variants such as `41...jpg`, `51...jpg`, and `71...jpg` as the same image when the remaining filename matches; keep the candidate with the strongest size hint such as `SL1500`.
- Do not download customer-review images or images from related/sponsored products.
- Do not include swatches, videos, icons, badges, review images, recommendation images, or images from comparison widgets.
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

Each product folder must contain only that product's final unique gallery images, `product-details.docx`, `product-data.json`, and optional `image-errors.json`. Do not create nested product folders or extra subfolders inside a product folder. The bundled script performs a final cleanup after download: when two saved files have the same Amazon image identity, it keeps the larger file and removes the smaller duplicate, then renumbers the remaining images.

## Quality checks

- Confirm the number of unique product URLs collected across all pages.
- For a small catalog, compare the export folders to every discovered ASIN. For a large catalog, compare counts and spot-check the first, middle, and last exported products.
- Open at least one generated Word file and verify that title, bullets, description, and source URL are readable.
- Verify downloaded files are actual high-resolution images and not thumbnails or HTML challenge pages; the script rejects non-image responses and removes duplicate binary files.
- Spot-check one exported product folder: repeated-looking images should not appear as the same base image in different sizes, and image count should roughly match the Amazon product gallery rather than thumbnail repetitions.
- Never claim completeness when pagination was blocked or interrupted. State the last completed page and partial counts.
