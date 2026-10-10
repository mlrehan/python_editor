"""
Design System, Themes, and CSS Styles for Python Cloud Studio User Guide.
Fully self-contained, no external CSS or Google Fonts required.
"""

def get_css():
    return """
/* === ENTERPRISE DESIGN TOKENS & ROOT VARIABLES === */
:root {
  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;

  /* Light Theme (Default) */
  --bg-body: #f8fafc;
  --bg-surface: #ffffff;
  --bg-surface-elevated: #ffffff;
  --bg-sidebar: #f1f5f9;
  --bg-sidebar-hover: #e2e8f0;
  --bg-sidebar-active: #e2e8f0;
  --bg-input: #ffffff;
  --bg-code: #0f172a;
  --text-code: #f8fafc;

  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #64748b;
  --text-inverse: #ffffff;

  --border-color: #e2e8f0;
  --border-secondary: #cbd5e1;
  --border-focus: #2563eb;

  --primary-blue: #2563eb;
  --primary-blue-hover: #1d4ed8;
  --primary-blue-light: #eff6ff;
  --primary-blue-border: #bfdbfe;

  --accent-purple: #7c3aed;
  --accent-purple-light: #f5f3ff;

  --success-green: #16a34a;
  --success-light: #f0fdf4;
  --success-border: #bbf7d0;

  --warning-amber: #d97706;
  --warning-light: #fffbeb;
  --warning-border: #fde68a;

  --danger-red: #dc2626;
  --danger-light: #fef2f2;
  --danger-border: #fecaca;

  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);

  --header-height: 60px;
  --sidebar-width: 290px;
  --toc-width: 220px;
  --content-max-width: 900px;
  --transition-fast: 0.15s ease;
}

[data-theme="dark"] {
  --bg-body: #0b1220;
  --bg-surface: #111827;
  --bg-surface-elevated: #1e293b;
  --bg-sidebar: #0f172a;
  --bg-sidebar-hover: #1e293b;
  --bg-sidebar-active: #1e293b;
  --bg-input: #1e293b;
  --bg-code: #030712;
  --text-code: #f1f5f9;

  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --text-inverse: #0f172a;

  --border-color: #334155;
  --border-secondary: #475569;
  --border-focus: #3b82f6;

  --primary-blue: #3b82f6;
  --primary-blue-hover: #60a5fa;
  --primary-blue-light: rgba(59, 130, 246, 0.15);
  --primary-blue-border: #1e40af;

  --accent-purple: #a855f7;
  --accent-purple-light: rgba(168, 85, 247, 0.15);

  --success-green: #22c55e;
  --success-light: rgba(34, 197, 94, 0.15);
  --success-border: #166534;

  --warning-amber: #f59e0b;
  --warning-light: rgba(245, 158, 11, 0.15);
  --warning-border: #92400e;

  --danger-red: #ef4444;
  --danger-light: rgba(239, 68, 68, 0.15);
  --danger-border: #991b1b;

  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.6);
}

/* === BASE & RESET === */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-primary);
  background-color: var(--bg-body);
  scroll-behavior: smooth;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

a {
  color: var(--primary-blue);
  text-decoration: none;
  transition: color var(--transition-fast);
}

a:hover {
  text-decoration: underline;
}

p {
  margin-bottom: 1.15rem;
}

h1, h2, h3, h4, h5, h6 {
  color: var(--text-primary);
  font-weight: 700;
  line-height: 1.3;
  margin-top: 1.8rem;
  margin-bottom: 0.8rem;
  scroll-margin-top: 80px;
}

h1 { font-size: 2.25rem; letter-spacing: -0.025em; margin-top: 0; }
h2 { font-size: 1.65rem; letter-spacing: -0.02em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.4rem; margin-top: 2.5rem; }
h3 { font-size: 1.3rem; margin-top: 1.8rem; }
h4 { font-size: 1.1rem; }

ul, ol {
  margin-bottom: 1.2rem;
  padding-left: 1.5rem;
}

li {
  margin-bottom: 0.4rem;
}

img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

/* === TOP HEADER === */
.docs-header {
  position: sticky;
  top: 0;
  z-index: 50;
  height: var(--header-height);
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  box-shadow: var(--shadow-sm);
  transition: background-color var(--transition-fast), border-color var(--transition-fast);
}

.reading-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, #2563eb, #7c3aed);
  width: 0%;
  transition: width 0.1s ease;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text-primary);
  text-decoration: none !important;
}

.brand-icon {
  width: 32px;
  height: 32px;
  background-color: #2563eb;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(37,99,235,0.4);
}

.brand-subtitle {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--primary-blue);
  background-color: var(--primary-blue-light);
  border: 1px solid var(--primary-blue-border);
  padding: 2px 8px;
  border-radius: 999px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.header-search-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background-color: var(--bg-body);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 0.88rem;
  cursor: pointer;
  width: 260px;
  transition: all var(--transition-fast);
}

.header-search-btn:hover {
  border-color: var(--primary-blue);
  color: var(--text-primary);
  background-color: var(--bg-surface);
}

.search-kbd {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  padding: 1px 5px;
  border-radius: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.theme-toggle-btn, .print-btn, .app-link-btn, .mobile-toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background-color: var(--bg-body);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none !important;
}

.theme-toggle-btn:hover, .print-btn:hover {
  background-color: var(--bg-sidebar);
  color: var(--text-primary);
  border-color: var(--border-secondary);
}

.app-link-btn {
  background-color: var(--primary-blue);
  color: #ffffff !important;
  border-color: var(--primary-blue);
  font-weight: 600;
}

.app-link-btn:hover {
  background-color: var(--primary-blue-hover);
}

.mobile-toggle-btn {
  display: none;
  padding: 6px 8px;
}

/* === MAIN 3-COLUMN LAYOUT === */
.docs-layout, .docs-container {
  display: flex;
  flex: 1;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  position: relative;
}

/* === LEFT SIDEBAR === */
.docs-sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  height: calc(100vh - var(--header-height));
  position: sticky;
  top: var(--header-height);
  overflow-y: auto;
  border-right: 1px solid var(--border-color);
  background-color: var(--bg-sidebar);
  padding: 1.5rem 1rem 3rem 1.25rem;
  transition: transform var(--transition-fast), background-color var(--transition-fast);
}

.sidebar-category {
  margin-bottom: 1.5rem;
}

.sidebar-category-header {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  padding-left: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
}

.sidebar-nav-list {
  list-style: none;
  padding-left: 0;
}

.sidebar-nav-item {
  margin-bottom: 2px;
}

.sidebar-nav-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.88rem;
  font-weight: 500;
  text-decoration: none !important;
  transition: all var(--transition-fast);
}

.sidebar-nav-link:hover {
  color: var(--text-primary);
  background-color: var(--bg-sidebar-hover);
}

.sidebar-nav-link.active {
  color: var(--primary-blue);
  background-color: var(--primary-blue-light);
  font-weight: 600;
}

.sidebar-nav-badge {
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: auto;
  font-weight: 600;
}

.badge-tutorial { background-color: var(--accent-purple-light); color: var(--accent-purple); }
.badge-verified { background-color: var(--success-light); color: var(--success-green); }
.badge-admin { background-color: var(--warning-light); color: var(--warning-amber); }

/* === MAIN CONTENT ARTICLE === */
.docs-main {
  flex: 1;
  min-width: 0;
  padding: 2.5rem 3rem 5rem 3rem;
  background-color: var(--bg-surface);
  border-right: 1px solid var(--border-color);
}

.content-wrapper {
  max-width: var(--content-max-width);
  margin: 0 auto;
}

/* === RIGHT TABLE OF CONTENTS === */
.docs-toc {
  width: var(--toc-width);
  flex-shrink: 0;
  height: calc(100vh - var(--header-height));
  position: sticky;
  top: var(--header-height);
  overflow-y: auto;
  padding: 2rem 1.25rem;
  font-size: 0.82rem;
}

.toc-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 0.8rem;
}

.toc-list {
  list-style: none;
  padding-left: 0;
  border-left: 2px solid var(--border-color);
}

.toc-item {
  margin-bottom: 0.5rem;
}

.toc-link {
  display: block;
  padding: 3px 0 3px 12px;
  color: var(--text-muted);
  text-decoration: none !important;
  transition: color var(--transition-fast);
  margin-left: -2px;
}

.toc-link:hover, .toc-link.active {
  color: var(--primary-blue);
  border-left: 2px solid var(--primary-blue);
  font-weight: 600;
}

/* === HERO SECTION ON HOME PAGE === */
.hero-banner {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(124, 58, 237, 0.08) 100%);
  border: 1px solid var(--primary-blue-border);
  border-radius: 12px;
  padding: 2.5rem 2rem;
  margin-bottom: 2.5rem;
}

.hero-eyebrow {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--primary-blue);
  margin-bottom: 0.6rem;
}

.hero-title {
  font-size: 2.4rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-top: 0;
  margin-bottom: 0.8rem;
  letter-spacing: -0.03em;
}

.hero-subtitle {
  font-size: 1.15rem;
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
  max-width: 680px;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.btn-primary-action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background-color: var(--primary-blue);
  color: #ffffff !important;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none !important;
  box-shadow: 0 2px 8px rgba(37,99,235,0.3);
  transition: background-color var(--transition-fast);
}

.btn-primary-action:hover {
  background-color: var(--primary-blue-hover);
}

.btn-secondary-action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background-color: var(--bg-surface);
  color: var(--text-primary) !important;
  border: 1px solid var(--border-color);
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none !important;
  transition: all var(--transition-fast);
}

.btn-secondary-action:hover {
  background-color: var(--bg-sidebar);
  border-color: var(--border-secondary);
}

/* === QUICK CARDS GRID === */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin: 1.5rem 0 2.5rem 0;
}

.doc-card {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1.4rem;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast);
  display: flex;
  flex-direction: column;
}

.doc-card:hover {
  border-color: var(--primary-blue);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.doc-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.card-icon-blue { background-color: var(--primary-blue-light); color: var(--primary-blue); }
.card-icon-purple { background-color: var(--accent-purple-light); color: var(--accent-purple); }
.card-icon-green { background-color: var(--success-light); color: var(--success-green); }
.card-icon-amber { background-color: var(--warning-light); color: var(--warning-amber); }

.doc-card-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-top: 0;
  margin-bottom: 6px;
}

.doc-card-desc {
  font-size: 0.88rem;
  color: var(--text-secondary);
  margin-bottom: 12px;
  flex: 1;
}

.doc-card-link {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--primary-blue);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* === CALLOUT BOXES === */
.callout {
  border-radius: 8px;
  padding: 1.15rem 1.25rem;
  margin: 1.4rem 0;
  display: flex;
  gap: 14px;
  font-size: 0.92rem;
  line-height: 1.55;
}

.callout-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.callout-body {
  flex: 1;
}

.callout-title {
  font-weight: 700;
  margin-bottom: 4px;
  font-size: 0.95rem;
}

.callout p:last-child {
  margin-bottom: 0;
}

.callout-tip {
  background-color: var(--primary-blue-light);
  border-left: 4px solid var(--primary-blue);
  color: var(--text-primary);
}
.callout-tip .callout-title { color: var(--primary-blue); }

.callout-important {
  background-color: var(--warning-light);
  border-left: 4px solid var(--warning-amber);
  color: var(--text-primary);
}
.callout-important .callout-title { color: var(--warning-amber); }

.callout-warning {
  background-color: var(--danger-light);
  border-left: 4px solid var(--danger-red);
  color: var(--text-primary);
}
.callout-warning .callout-title { color: var(--danger-red); }

.callout-success {
  background-color: var(--success-light);
  border-left: 4px solid var(--success-green);
  color: var(--text-primary);
}
.callout-success .callout-title { color: var(--success-green); }

/* === CODE BLOCKS & SYNTAX HIGHLIGHTING === */
.code-container {
  background-color: var(--bg-code);
  border-radius: 8px;
  overflow: hidden;
  margin: 1.2rem 0;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background-color: rgba(0, 0, 0, 0.25);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.code-lang-badge {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.copy-btn {
  background-color: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #e2e8f0;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all var(--transition-fast);
}

.copy-btn:hover {
  background-color: rgba(255, 255, 255, 0.18);
  color: #ffffff;
}

.copy-btn.copied {
  background-color: #16a34a;
  border-color: #16a34a;
  color: #ffffff;
}

pre {
  padding: 1rem 1.25rem;
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--text-code);
}

code {
  font-family: var(--font-mono);
}

:not(pre) > code {
  font-size: 0.86em;
  padding: 2px 6px;
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--primary-blue);
}

/* Syntax Highlighting Tokens */
.syn-kw { color: #f43f5e; font-weight: 600; }
.syn-str { color: #34d399; }
.syn-num { color: #fb923c; }
.syn-com { color: #64748b; font-style: italic; }
.syn-fn { color: #38bdf8; }
.syn-var { color: #f8fafc; }

/* === EXPECTED OUTPUT BOX === */
.expected-output {
  background-color: #030712;
  border: 1px solid #1f2937;
  border-left: 4px solid #10b981;
  border-radius: 6px;
  margin: -0.6rem 0 1.4rem 0;
  padding: 10px 14px;
}

.output-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #10b981;
  margin-bottom: 6px;
}

.output-text {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-all;
}

/* === MISTAKE COMPARISON GRID === */
.mistake-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 1.4rem 0;
}

.mistake-card {
  border-radius: 8px;
  padding: 1.2rem;
  border: 1px solid var(--border-color);
}

.mistake-wrong {
  background-color: var(--danger-light);
  border-color: var(--danger-border);
}

.mistake-correct {
  background-color: var(--success-light);
  border-color: var(--success-border);
}

.mistake-badge {
  font-weight: 700;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.mistake-wrong .mistake-badge { color: var(--danger-red); }
.mistake-correct .mistake-badge { color: var(--success-green); }

/* === NUMBERED STEP FLOW === */
.step-list {
  list-style: none;
  padding-left: 0;
  counter-reset: step-counter;
  margin: 1.5rem 0;
}

.step-item {
  position: relative;
  counter-increment: step-counter;
  padding-left: 48px;
  margin-bottom: 1.8rem;
}

.step-item::before {
  content: counter(step-counter);
  position: absolute;
  left: 0;
  top: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--primary-blue);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.9rem;
  box-shadow: 0 2px 6px rgba(37,99,235,0.4);
}

.step-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: 6px;
}

/* === INTERFACE DIAGRAMS === */
.ui-diagram {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
  margin: 1.8rem 0;
  box-shadow: var(--shadow-md);
}

.ui-diagram-header {
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  padding: 8px 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
}

.ui-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.ui-dot-red { background-color: #ef4444; }
.ui-dot-amber { background-color: #f59e0b; }
.ui-dot-green { background-color: #10b981; }

.ui-diagram-body {
  padding: 1.5rem;
}

.callout-pin {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: #ef4444;
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 700;
  margin-right: 6px;
  vertical-align: middle;
}

/* === TABLES === */
.doc-table-container {
  width: 100%;
  overflow-x: auto;
  margin: 1.4rem 0;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  text-align: left;
}

.doc-table th {
  background-color: var(--bg-sidebar);
  padding: 10px 14px;
  font-weight: 700;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
}

.doc-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.doc-table tr:last-child td {
  border-bottom: none;
}

.doc-table tr:hover td {
  background-color: var(--primary-blue-light);
}

kbd {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
  box-shadow: 0 1px 0 rgba(0,0,0,0.2);
  color: var(--text-primary);
}

/* === ACCORDION DETAILS === */
details.doc-accordion {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin: 1rem 0;
  overflow: hidden;
  background-color: var(--bg-surface);
}

details.doc-accordion summary {
  padding: 12px 16px;
  font-weight: 600;
  cursor: pointer;
  background-color: var(--bg-sidebar);
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-primary);
}

details.doc-accordion summary::-webkit-details-marker {
  display: none;
}

details.doc-accordion[open] summary {
  border-bottom: 1px solid var(--border-color);
}

.accordion-content {
  padding: 16px;
}

/* === SEARCH MODAL === */
.search-modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: none;
  align-items: flex-start;
  justify-content: center;
  padding-top: 10vh;
}

.search-modal-backdrop.active {
  display: flex;
}

.search-modal {
  width: 90%;
  max-width: 620px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  animation: modal-pop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modal-pop {
  from { opacity: 0; transform: scale(0.96) translateY(-10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-color);
  gap: 12px;
}

.search-modal-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.search-results-list {
  max-height: 420px;
  overflow-y: auto;
  padding: 8px;
  list-style: none;
}

.search-result-item {
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 3px;
  text-decoration: none !important;
  color: var(--text-primary);
  transition: background-color var(--transition-fast);
}

.search-result-item:hover, .search-result-item.selected {
  background-color: var(--primary-blue-light);
}

.search-result-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--primary-blue);
}

.search-result-category {
  font-size: 0.72rem;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}

.search-result-snippet {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.search-footer {
  padding: 8px 16px;
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
  font-size: 0.78rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* === BACK TO TOP BUTTON === */
.back-to-top-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background-color: var(--primary-blue);
  color: #ffffff;
  border: none;
  box-shadow: var(--shadow-lg);
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 40;
  transition: transform var(--transition-fast), background-color var(--transition-fast);
}

.back-to-top-btn.visible {
  display: flex;
}

.back-to-top-btn:hover {
  transform: translateY(-3px);
  background-color: var(--primary-blue-hover);
}

/* === FOOTER === */
.docs-footer {
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
  padding: 3rem 2rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.88rem;
}

/* === CUSTOM GUIDE COMPONENTS, BADGES & DIAGRAMS === */
.search-modal-backdrop.open {
  display: flex !important;
}

.search-result-item.highlighted {
  background-color: var(--primary-blue-light) !important;
}

.search-result-item .result-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--primary-blue);
}

.search-result-item .result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.search-result-item .result-badge {
  background: var(--bg-sidebar);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.search-result-item .result-url {
  font-family: var(--font-mono);
}

/* Hero Section */
.hero-section {
  padding: 3rem 0 2.5rem 0;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 3rem;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background-color: var(--primary-blue-light);
  color: var(--primary-blue);
  border: 1px solid var(--primary-blue-border);
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 1.25rem;
}

.hero-title {
  font-size: 2.75rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin-bottom: 1rem;
  line-height: 1.15;
}

.hero-subtitle {
  font-size: 1.2rem;
  line-height: 1.6;
  color: var(--text-secondary);
  max-width: 800px;
  margin-bottom: 2rem;
}

.hero-quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 2.5rem;
}

.quick-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text-primary);
  text-decoration: none;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.quick-chip:hover {
  border-color: var(--primary-blue);
  color: var(--primary-blue);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.hero-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1.25rem 1rem;
  text-align: center;
  box-shadow: var(--shadow-sm);
}

.stat-number {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--primary-blue);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-weight: 500;
}

/* Grids & Cards */
.two-column-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.25rem;
  margin: 1.5rem 0;
}

.three-column-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.25rem;
  margin: 1.5rem 0;
}

.feature-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
}

.feature-card-header {
  margin-bottom: 0.75rem;
}

.feature-card h4 {
  margin: 0 0 0.5rem 0;
  color: var(--text-primary);
  font-size: 1.05rem;
}

.feature-card p {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 0.75rem;
}

.feature-card ul {
  padding-left: 1.25rem;
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.88rem;
  line-height: 1.6;
}

/* Step Cards */
.step-card {
  display: flex;
  gap: 1.25rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1.5rem;
  margin: 1.25rem 0;
  box-shadow: var(--shadow-sm);
}

.step-num {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--primary-blue);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-content h4 {
  margin: 0 0 0.5rem 0;
  color: var(--text-primary);
}

/* Error Fix Cards */
.error-fix-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1.5rem;
  margin: 1.5rem 0;
  box-shadow: var(--shadow-sm);
}

.error-badge-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.error-frequency {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}

/* Custom Badges */
.badge-guest {
  background: rgba(14, 165, 233, 0.15);
  color: #0284c7;
  border: 1px solid rgba(14, 165, 233, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 600;
}

.badge-idle {
  background: var(--success-light);
  color: var(--success-green);
  border: 1px solid var(--success-border);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 600;
}

.badge-busy {
  background: var(--warning-light);
  color: var(--warning-amber);
  border: 1px solid var(--warning-border);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 600;
}

.badge-restarting {
  background: var(--primary-blue-light);
  color: var(--primary-blue);
  border: 1px solid var(--primary-blue-border);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 600;
  animation: pulse 1.5s infinite;
}

.badge-disconnected {
  background: var(--danger-light);
  color: var(--danger-red);
  border: 1px solid var(--danger-border);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 600;
}

.badge-tutorial {
  background: var(--accent-purple-light);
  color: var(--accent-purple);
  border: 1px solid rgba(168, 85, 247, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 600;
}

.badge-error {
  background: var(--danger-light);
  color: var(--danger-red);
  border: 1px solid var(--danger-border);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
  font-family: var(--font-mono);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Diagram Containers */
.diagram-container {
  margin: 2rem 0;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.diagram-title {
  padding: 10px 16px;
  background: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

/* App Wireframe */
.app-layout-wireframe {
  padding: 1.5rem;
  font-family: var(--font-sans);
}

.wireframe-navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: var(--bg-body);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 1rem;
}

.wf-logo {
  font-weight: 700;
  color: var(--primary-blue);
  margin-right: 8px;
}

.wf-badge {
  background: var(--primary-blue-light);
  color: var(--primary-blue);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.72rem;
}

.wf-pill {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  margin: 0 3px;
}

.wireframe-body {
  display: grid;
  grid-template-columns: 200px 1fr 220px;
  gap: 12px;
}

@media (max-width: 800px) {
  .wireframe-body { grid-template-columns: 1fr; }
}

.wireframe-sidebar-left, .wireframe-panel-right {
  background: var(--bg-body);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  font-size: 0.8rem;
}

.wf-header {
  font-weight: 700;
  color: var(--text-muted);
  margin-bottom: 8px;
  font-size: 0.75rem;
}

.wf-actions {
  color: var(--primary-blue);
  font-size: 0.72rem;
  margin-bottom: 8px;
}

.wf-tree {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  line-height: 1.7;
}

.wireframe-editor-center {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
}

.wf-notebook-header {
  display: flex;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 12px;
  font-size: 0.82rem;
}

.wf-cell {
  display: flex;
  background: var(--bg-code);
  color: var(--text-code);
  border-radius: 6px;
  padding: 10px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  margin-bottom: 8px;
}

.wf-cell-gutter {
  color: #10b981;
  font-weight: 700;
  margin-right: 12px;
}

.wf-cell-output {
  background: var(--bg-body);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 8px;
  font-size: 0.75rem;
}

.wf-resize-handle {
  text-align: center;
  font-size: 0.7rem;
  color: var(--text-muted);
  padding: 6px 0;
  cursor: row-resize;
}

/* Autocomplete Simulation */
.autocomplete-sim-box {
  background: var(--bg-code);
  color: var(--text-code);
  padding: 1.5rem;
  font-family: var(--font-mono);
  position: relative;
}

.sim-editor-line {
  line-height: 1.8;
  font-size: 0.95rem;
}

.syn-keyword { color: #f43f5e; font-weight: 600; }
.syn-var { color: #38bdf8; }

.sim-cursor {
  display: inline-block;
  width: 2px;
  height: 1.1em;
  background: #38bdf8;
  vertical-align: middle;
  animation: blink 1s infinite;
}

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

.sim-dropdown {
  margin-top: 6px;
  background: var(--bg-surface-elevated);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.sim-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  font-size: 0.82rem;
  color: var(--text-primary);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.sim-item.active {
  background: var(--primary-blue-light);
  color: var(--primary-blue);
  border-left: 3px solid var(--primary-blue);
}

.sim-icon-func {
  background: #3b82f6;
  color: #fff;
  width: 18px;
  height: 18px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
}

.sim-desc {
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-left: auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 240px;
}

/* DataTableView Mockup */
.table-view-mockup {
  padding: 1.25rem;
  background: var(--bg-surface);
}

.tv-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
  flex-wrap: wrap;
}

.tv-search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 6px 12px;
  flex: 1;
  max-width: 320px;
}

.tv-search-box input {
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 0.85rem;
  width: 100%;
}

.tv-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tv-pill-action {
  background: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.tv-page-select {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.tv-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.tv-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.tv-table th {
  background: var(--bg-sidebar);
  padding: 10px 14px;
  text-align: left;
  border-bottom: 2px solid var(--border-color);
  color: var(--text-primary);
  font-weight: 600;
}

.tv-sort-icon {
  color: var(--primary-blue);
  font-size: 0.7rem;
}

.tv-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.tv-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.tv-pagination {
  display: flex;
  gap: 4px;
}

.tv-btn {
  padding: 4px 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
}

.tv-page-num.active {
  padding: 4px 10px;
  background: var(--primary-blue);
  color: #fff;
  border-radius: 4px;
  font-size: 0.75rem;
}

/* State Diagram */
.state-diagram-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 2rem 1rem;
  gap: 12px;
  flex-wrap: wrap;
}

.cell-node, .kernel-node {
  background: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  text-align: center;
}

.node-title, .kernel-title {
  font-weight: 700;
  font-size: 0.88rem;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.node-code, .kernel-vars {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--primary-blue);
}

.node-arrow {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.82rem;
}

/* Chart Simulation */
.chart-sim-box {
  padding: 1.5rem;
  background: var(--bg-surface);
}

.chart-svg {
  width: 100%;
  height: auto;
  max-height: 240px;
}

/* Glossary */
.glossary-list dt {
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--primary-blue);
  margin-top: 1.25rem;
}

.glossary-list dd {
  margin-left: 0;
  color: var(--text-secondary);
  line-height: 1.6;
  font-size: 0.92rem;
  margin-bottom: 0.75rem;
}

/* Code Copy */
.code-copy-btn.copied {
  background-color: var(--success-green) !important;
  color: #ffffff !important;
}

/* === RESPONSIVE BREAKPOINTS === */
@media (max-width: 1200px) {
  .docs-toc {
    display: none;
  }
  .docs-main {
    border-right: none;
  }
}

@media (max-width: 900px) {
  .docs-sidebar {
    position: fixed;
    top: var(--header-height);
    left: 0;
    bottom: 0;
    width: 290px;
    max-width: 85vw;
    background-color: var(--bg-surface);
    border-right: 1px solid var(--border-color);
    z-index: 60;
    transform: translateX(-100%);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.35);
  }
  .docs-sidebar.open {
    transform: translateX(0);
  }
  .mobile-toggle-btn {
    display: flex;
  }
  .header-search-btn {
    width: 170px;
  }
  .docs-main {
    padding: 2rem 1.25rem 4rem 1.25rem;
  }
}

@media (max-width: 600px) {
  .header-search-btn {
    display: none;
  }
  .print-btn {
    display: none;
  }
  .brand-subtitle {
    display: none;
  }
  .brand-badge {
    white-space: nowrap;
    font-size: 0.92rem;
  }
  .app-link-btn span {
    display: none;
  }
  .app-link-btn {
    padding: 6px 8px;
  }
  .hero-title {
    font-size: 1.85rem;
  }
  .docs-main {
    padding: 1.5rem 1rem 3rem 1rem;
  }
}

/* === PRINT STYLESHEET === */
@media print {
  body {
    background-color: #ffffff !important;
    color: #000000 !important;
    font-size: 11pt;
  }
  .docs-header, .docs-sidebar, .docs-toc, .back-to-top-btn, .search-modal-backdrop, .reading-progress-bar, .copy-btn {
    display: none !important;
  }
  .docs-main {
    padding: 0 !important;
    border: none !important;
  }
  .content-wrapper {
    max-width: 100% !important;
  }
  h1, h2, h3 {
    color: #000000 !important;
    page-break-after: avoid;
  }
  .code-container, .expected-output, .callout, .doc-card, .mistake-card {
    border: 1px solid #cccccc !important;
    background-color: #f9f9f9 !important;
    color: #000000 !important;
    page-break-inside: avoid;
    box-shadow: none !important;
  }
  pre, code, .output-text {
    color: #000000 !important;
  }
  a {
    color: #000000 !important;
    text-decoration: underline;
  }
}
"""
