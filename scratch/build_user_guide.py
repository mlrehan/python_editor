"""
Build script to compile the complete single-file standalone user guide HTML.
"""
import os
import sys

# Add current folder to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from guide_parts.styles import get_css
from guide_parts.header_nav import get_header, get_sidebar
from guide_parts.hero import get_hero
from guide_parts.ch1_to_5 import get_chapters_1_to_5
from guide_parts.ch6_to_9 import get_chapters_6_to_9
from guide_parts.ch10_to_14 import get_chapters_10_to_14
from guide_parts.ch15_to_20 import get_chapters_15_to_20
from guide_parts.ch21_to_28 import get_chapters_21_to_28
from guide_parts.tutorials import get_tutorials
from guide_parts.scripts import get_scripts

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "python-cloud-studio-user-guide.html")

def build_guide():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Gathering guide modules...")
    css = get_css()
    header = get_header()
    sidebar = get_sidebar()
    hero = get_hero()
    ch1_5 = get_chapters_1_to_5()
    ch6_9 = get_chapters_6_to_9()
    ch10_14 = get_chapters_10_to_14()
    ch15_20 = get_chapters_15_to_20()
    ch21_28 = get_chapters_21_to_28()
    tutorials = get_tutorials()
    scripts = get_scripts()
    
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Python Cloud Studio - Official Enterprise User Guide & Beginner Training Manual">
  <title>Python Cloud Studio — Official User Guide & Training Manual</title>
  <style>
{css}
  </style>
</head>
<body>
{header}

<div class="docs-layout">
{sidebar}

  <main class="docs-main" id="mainContent" role="main">
    <div class="content-wrapper">
{hero}
{ch1_5}
{ch6_9}
{ch10_14}
{ch15_20}
{ch21_28}
{tutorials}
    </div>

    <footer class="docs-footer">
      <p><strong>Python Cloud Studio</strong> &copy; 2026. Enterprise Cloud Notebook &amp; Data Analysis Platform.</p>
      <p style="margin-top: 6px; font-size: 0.82rem; color: var(--text-muted);">
        Completely self-contained offline documentation manual. Zero external CDNs or remote dependencies.
      </p>
    </footer>
  </main>
</div>

<!-- Back to Top Button -->
<button class="back-to-top-btn" id="backToTopBtn" aria-label="Back to top" title="Back to top" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="18 15 12 9 6 15"></polyline>
  </svg>
</button>

{scripts}
</body>
</html>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
        
    size_bytes = os.path.getsize(OUTPUT_FILE)
    print(f"Successfully compiled standalone HTML user guide!")
    print(f"Target: {OUTPUT_FILE}")
    print(f"File size: {size_bytes / 1024:.1f} KB ({size_bytes:,} bytes)")

if __name__ == "__main__":
    build_guide()

