#!/usr/bin/env python3
"""Save one Amazon product record as images, JSON, and a minimal DOCX."""

import argparse
import hashlib
import json
import mimetypes
import re
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
AMAZON_IMAGE_MARKER = re.compile(r"\._[^/]*_\.")
AMAZON_IMAGE_EXT = re.compile(r"(\.(?:jpg|jpeg|png|webp))(?:$|\?)", re.IGNORECASE)


def safe_name(value: str, limit: int = 100) -> str:
    value = INVALID.sub(" ", value or "Untitled product")
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:limit].rstrip(" .") or "Untitled product")


def paragraph(text: str, style: str | None = None) -> str:
    props = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    lines = str(text or "").splitlines() or [""]
    runs = "<w:br/>".join(
        f'<w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r>' for line in lines
    )
    return f"<w:p>{props}{runs}</w:p>"


def make_docx(path: Path, item: dict) -> None:
    bullets = item.get("bullet_points") or []
    body = [paragraph(item.get("title", ""), "Title")]
    body += [paragraph("ASIN", "Heading1"), paragraph(item.get("asin", ""))]
    body += [paragraph("Bullet Points", "Heading1")]
    body += [paragraph(f"• {point}") for point in bullets] or [paragraph("")]
    body += [paragraph("Product Description", "Heading1"), paragraph(item.get("description", ""))]
    body += [paragraph("Source URL", "Heading1"), paragraph(item.get("source_url", ""))]
    document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{''.join(body)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:sz w:val="22"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style></w:styles>'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as doc:
        doc.writestr("[Content_Types].xml", content_types)
        doc.writestr("_rels/.rels", rels)
        doc.writestr("word/document.xml", document)
        doc.writestr("word/styles.xml", styles)
        doc.writestr("word/_rels/document.xml.rels", doc_rels)


def normalize_amazon_image_url(url: str) -> str:
    """Return the highest-quality stable form of an Amazon image URL."""
    parsed = urllib.parse.urlparse(str(url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = urllib.parse.unquote(parsed.path)

    if "media-amazon." in parsed.netloc or "ssl-images-amazon." in parsed.netloc:
        path = AMAZON_IMAGE_MARKER.sub(".", path)
        match = AMAZON_IMAGE_EXT.search(path)
        if match:
            path = path[: match.end(1)]

    path = urllib.parse.quote(path, safe="/._-")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def image_identity(url: str) -> str:
    normalized = normalize_amazon_image_url(url)
    parsed = urllib.parse.urlparse(normalized)
    path = parsed.path.lower()
    if "media-amazon." in parsed.netloc or "ssl-images-amazon." in parsed.netloc:
        path = AMAZON_IMAGE_MARKER.sub(".", path)
        match = AMAZON_IMAGE_EXT.search(path)
        if match:
            path = path[: match.end(1)]
    return f"{parsed.netloc.lower()}{path}"


def unique_image_urls(urls: list[str]) -> list[str]:
    unique = {}
    for url in urls or []:
        normalized = normalize_amazon_image_url(url)
        if not normalized:
            continue
        key = image_identity(normalized)
        unique.setdefault(key, normalized)
    return list(unique.values())


def download_image(url: str, stem: Path) -> tuple[Path, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "image/*"})
    with urllib.request.urlopen(request, timeout=45) as response:
        content_type = response.headers.get_content_type().lower()
        if not content_type.startswith("image/"):
            raise ValueError(f"non-image response: {content_type}")
        data = response.read()
    if not data:
        raise ValueError("empty image response")
    ext = mimetypes.guess_extension(content_type) or Path(urllib.parse.urlparse(url).path).suffix or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"
    target = stem.with_suffix(ext)
    target.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    return target, digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    item = json.loads(args.input.read_text(encoding="utf-8-sig"))
    asin = safe_name(str(item.get("asin") or "NO-ASIN"), 24)
    folder = args.output / f"{asin} - {safe_name(str(item.get('title') or ''), 100)}"
    folder.mkdir(parents=True, exist_ok=True)
    item["image_urls"] = unique_image_urls(item.get("image_urls") or [])
    (folder / "product-data.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    make_docx(folder / "product-details.docx", item)
    failures = []
    downloaded_hashes = {}
    saved = 0
    for index, url in enumerate(item.get("image_urls") or [], 1):
        try:
            target, digest = download_image(url, folder / f"{index:02d}")
            if digest in downloaded_hashes:
                target.unlink(missing_ok=True)
                continue
            downloaded_hashes[digest] = str(target.name)
            saved += 1
        except Exception as exc:
            failures.append({"url": url, "error": str(exc)})
    if failures:
        (folder / "image-errors.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"folder": str(folder), "images_saved": saved, "image_failures": len(failures)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
