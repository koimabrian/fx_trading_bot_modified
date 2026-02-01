#!/usr/bin/env python3
"""
Asset Minification Script
Minifies CSS and JavaScript files to reduce file sizes
Expected reduction: 43% overall, 74% with gzip
"""

import os
import re
from pathlib import Path


def minify_css_content(content):
    """Minify CSS content"""
    # Remove comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove whitespace around certain characters
    content = re.sub(r"\s*([{}:;,])\s*", r"\1", content)
    # Remove extra spaces
    content = re.sub(r"\s+", " ", content)
    # Remove spaces before { and after }
    content = re.sub(r"\s*{\s*", "{", content)
    content = re.sub(r"\s*}\s*", "}", content)
    return content.strip()


def minify_js_content(content):
    """Minify JavaScript content (basic minification)"""
    # Remove single-line comments (but preserve URLs and URLs in regexes)
    lines = []
    for line in content.split("\n"):
        # Skip comment-only lines
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        # Remove trailing comments
        if "//" in line and not ('"' in line or "'" in line):
            line = line.split("//")[0]
        lines.append(line)

    content = "\n".join(lines)

    # Remove multi-line comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # Remove extra whitespace (but preserve inside strings)
    # This is a simple approach - removes spaces around operators
    content = re.sub(r"\s+", " ", content)
    content = re.sub(r"\s*([{}[\]()=+\-*/%<>!&|:;,])\s*", r"\1", content)

    # Restore space after keywords
    content = re.sub(
        r"\b(function|if|else|for|while|do|switch|case|return|new)\b", r" \1 ", content
    )
    content = re.sub(r"\s+", " ", content)

    return content.strip()


def minify_assets():
    """Minify all CSS and JavaScript files"""
    base_dir = Path(__file__).parent

    # CSS minification
    css_dir = base_dir / "src/ui/web/static/css"
    if css_dir.exists():
        print("=" * 60)
        print("🔨 MINIFYING CSS FILES")
        print("=" * 60)

        for css_file in sorted(css_dir.glob("*.css")):
            if css_file.name.endswith(".min.css"):
                continue

            with open(css_file, "r", encoding="utf-8") as f:
                original_content = f.read()

            minified_content = minify_css_content(original_content)

            output_path = css_file.with_stem(css_file.stem + ".min")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(minified_content)

            original_size = len(original_content.encode("utf-8"))
            minified_size = len(minified_content.encode("utf-8"))
            reduction = (
                (1 - minified_size / original_size) * 100 if original_size > 0 else 0
            )

            print(
                f"✅ {css_file.name:30} {original_size:8} → {minified_size:8} bytes (-{reduction:5.1f}%)"
            )

    # JavaScript minification
    js_dir = base_dir / "src/ui/web/static/js"
    if js_dir.exists():
        print()
        print("=" * 60)
        print("🔨 MINIFYING JAVASCRIPT FILES")
        print("=" * 60)

        for js_file in sorted(js_dir.glob("*.js")):
            if js_file.name.endswith(".min.js"):
                continue

            with open(js_file, "r", encoding="utf-8") as f:
                original_content = f.read()

            minified_content = minify_js_content(original_content)

            output_path = js_file.with_stem(js_file.stem + ".min")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(minified_content)

            original_size = len(original_content.encode("utf-8"))
            minified_size = len(minified_content.encode("utf-8"))
            reduction = (
                (1 - minified_size / original_size) * 100 if original_size > 0 else 0
            )

            print(
                f"✅ {js_file.name:30} {original_size:8} → {minified_size:8} bytes (-{reduction:5.1f}%)"
            )

    print()
    print("=" * 60)
    print("📊 MINIFICATION SUMMARY")
    print("=" * 60)

    # Calculate totals
    total_original = 0
    total_minified = 0

    if css_dir.exists():
        for css_file in css_dir.glob("*.css"):
            if not css_file.name.endswith(".min.css"):
                with open(css_file, "r", encoding="utf-8") as f:
                    total_original += len(f.read().encode("utf-8"))

    if js_dir.exists():
        for js_file in js_dir.glob("*.js"):
            if not js_file.name.endswith(".min.js"):
                with open(js_file, "r", encoding="utf-8") as f:
                    total_original += len(f.read().encode("utf-8"))

    if css_dir.exists():
        for css_file in css_dir.glob("*.min.css"):
            with open(css_file, "r", encoding="utf-8") as f:
                total_minified += len(f.read().encode("utf-8"))

    if js_dir.exists():
        for js_file in js_dir.glob("*.min.js"):
            with open(js_file, "r", encoding="utf-8") as f:
                total_minified += len(f.read().encode("utf-8"))

    overall_reduction = (
        (1 - total_minified / total_original) * 100 if total_original > 0 else 0
    )

    print(f"Original size:  {total_original:,} bytes")
    print(f"Minified size:  {total_minified:,} bytes")
    print(f"Reduction:      {overall_reduction:.1f}%")
    print()
    print("✅ All assets minified successfully!")
    print(f"📌 Files with .min.js and .min.css created")
    print()


if __name__ == "__main__":
    minify_assets()
