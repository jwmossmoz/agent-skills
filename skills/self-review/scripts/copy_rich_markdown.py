#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "beautifulsoup4>=4.12",
#   "markdown>=3.6",
#   "pyobjc-framework-Cocoa>=10.0; sys_platform == 'darwin'",
# ]
# ///
"""Copy Markdown to the macOS clipboard as rich HTML plus plain text."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import markdown
from bs4 import BeautifulSoup


def build_html(markdown_text: str) -> tuple[str, str]:
    """Return (html, plain_text) suitable for rich pasteboards."""
    body = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
    soup = BeautifulSoup(body, "html.parser")

    # Rich-text editors preserve real paragraphs more reliably than CSS margins.
    for tag in list(soup.find_all(["h2", "h3"])):
        spacer = soup.new_tag("p")
        spacer.append(soup.new_tag("br"))
        tag.insert_before(spacer)

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 14px; line-height: 1.45; }}
h1 {{ font-size: 20px; font-weight: 700; margin: 0 0 16px; }}
h2 {{ font-size: 17px; font-weight: 700; margin: 0 0 10px; }}
h3 {{ font-size: 14px; font-weight: 700; margin: 0 0 8px; }}
p {{ margin: 0 0 10px; }}
ul {{ margin: 0 0 14px 22px; padding: 0; }}
li {{ margin: 0 0 8px; }}
strong {{ font-weight: 700; }}
em {{ font-style: italic; }}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
</style>
</head>
<body>
{soup}
</body>
</html>
"""

    plain_parts: list[str] = []
    for el in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        if el.name == "p" and el.find("br") and not el.get_text(strip=True):
            plain_parts.append("")
            continue
        text = " ".join(el.get_text(" ", strip=True).split())
        if not text:
            continue
        if el.name == "li":
            plain_parts.append(f"- {text}")
        elif el.name in {"h1", "h2", "h3"}:
            if plain_parts and plain_parts[-1] != "":
                plain_parts.append("")
            plain_parts.append(text)
            plain_parts.append("")
        else:
            plain_parts.append(text)

    plain = "\n".join(plain_parts)
    while "\n\n\n" in plain:
        plain = plain.replace("\n\n\n", "\n\n")
    return html, plain.strip() + "\n"


def copy_to_clipboard(html: str, plain: str) -> list[str]:
    """Copy rich HTML and plain text to the macOS pasteboard."""
    try:
        from AppKit import NSPasteboard, NSPasteboardTypeHTML, NSPasteboardTypeString
    except Exception as exc:  # pragma: no cover - only fails off macOS/missing PyObjC
        raise RuntimeError(
            "AppKit/PyObjC is required for clipboard output on macOS"
        ) from exc

    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setString_forType_(html, NSPasteboardTypeHTML)
    pasteboard.setString_forType_(plain, NSPasteboardTypeString)
    return [str(t) for t in pasteboard.types()]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Markdown to review-form-friendly rich clipboard content."
    )
    parser.add_argument("markdown_file", type=Path, help="Markdown file to copy")
    parser.add_argument(
        "--html-out",
        type=Path,
        help="HTML output path. Defaults to <input-stem>-review-rich.html",
    )
    parser.add_argument(
        "--text-out",
        type=Path,
        help="Plain-text output path. Defaults to <input-stem>-review-rich.txt",
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Write output files without touching the clipboard.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    source = args.markdown_file.expanduser()
    markdown_text = source.read_text(encoding="utf-8")
    html, plain = build_html(markdown_text)

    html_out = args.html_out or source.with_name(f"{source.stem}-review-rich.html")
    text_out = args.text_out or source.with_name(f"{source.stem}-review-rich.txt")
    html_out.write_text(html, encoding="utf-8")
    text_out.write_text(plain, encoding="utf-8")

    print(f"wrote {html_out}")
    print(f"wrote {text_out}")

    if not args.no_clipboard:
        types = copy_to_clipboard(html, plain)
        print("copied rich HTML + plain text fallback to clipboard")
        print("pasteboard types:", ", ".join(types))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
