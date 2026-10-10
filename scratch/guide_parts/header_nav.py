"""
Header, Search Modal, and Navigation Sidebar for Python Cloud Studio User Guide.
"""

def get_header():
    return """
<!-- Reading Progress Bar -->
<div class="reading-progress-bar" id="readingProgress" aria-hidden="true"></div>

<!-- Top Sticky Header -->
<header class="docs-header" role="banner">
  <div class="header-left">
    <button class="mobile-toggle-btn" id="mobileMenuBtn" aria-label="Toggle navigation menu" title="Open Menu">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="3" y1="12" x2="21" y2="12"></line>
        <line x1="3" y1="6" x2="21" y2="6"></line>
        <line x1="3" y1="18" x2="21" y2="18"></line>
      </svg>
    </button>
    <a href="#hero" class="brand-badge">
      <div class="brand-icon" aria-hidden="true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="4 17 10 11 4 5"></polyline>
          <line x1="12" y1="19" x2="20" y2="19"></line>
        </svg>
      </div>
      <span>Python Cloud Studio</span>
      <span class="brand-subtitle">Official User Guide</span>
    </a>
  </div>

  <button class="header-search-btn" id="openSearchBtn" aria-label="Search documentation" title="Quick Search (Ctrl+K or /)">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="8"></circle>
      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    </svg>
    <span>Search guide & tutorials...</span>
    <span class="search-kbd">Ctrl K</span>
  </button>

  <div class="header-right">
    <button class="theme-toggle-btn" id="themeToggleBtn" aria-label="Toggle light and dark mode" title="Switch Theme">
      <svg id="themeIconSun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"></circle>
        <line x1="12" y1="1" x2="12" y2="3"></line>
        <line x1="12" y1="21" x2="12" y2="23"></line>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
        <line x1="1" y1="12" x2="3" y2="12"></line>
        <line x1="21" y1="12" x2="23" y2="12"></line>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
      </svg>
      <svg id="themeIconMoon" style="display:none;" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
      </svg>
      <span id="themeLabel">Theme</span>
    </button>

    <button class="print-btn" id="printDocBtn" aria-label="Print or save as PDF" title="Print Manual / Save as PDF">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 6 2 18 2 18 9"></polyline>
        <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
        <rect x="6" y="14" width="12" height="8"></rect>
      </svg>
      <span>Print / PDF</span>
    </button>

    <a href="http://localhost:8765" target="_blank" rel="noopener noreferrer" class="app-link-btn" title="Open the running Python Cloud Studio web application at http://localhost:8765">
      <span>Open Studio</span>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
        <polyline points="15 3 21 3 21 9"></polyline>
        <line x1="10" y1="14" x2="21" y2="3"></line>
      </svg>
    </a>
  </div>
</header>

<!-- Interactive Search Modal -->
<div class="search-modal-backdrop" id="searchModalBackdrop" role="dialog" aria-modal="true" aria-label="Search User Guide">
  <div class="search-modal">
    <div class="search-input-wrapper">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" color="var(--primary-blue)">
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
      </svg>
      <input type="text" class="search-modal-input" id="searchModalInput" placeholder="Search chapters, features, errors, shortcuts..." autocomplete="off" spellcheck="false" />
      <button id="closeSearchModalBtn" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:16px;">✕</button>
    </div>
    <ul class="search-results-list" id="searchResultsList" role="listbox">
      <!-- Search items rendered via JavaScript -->
    </ul>
    <div class="search-footer">
      <span>Type to search • Press <strong>Esc</strong> to close</span>
      <span>Client-Side Local Index</span>
    </div>
  </div>
</div>
"""

def get_sidebar():
    return """
<!-- Left Documentation Sidebar -->
<aside class="docs-sidebar" id="docsSidebar" role="navigation" aria-label="User Guide Navigation">
  
  <!-- Category 1 -->
  <div class="sidebar-category">
    <div class="sidebar-category-header">
      <span>1. Getting Started</span>
      <span class="badge badge-verified">Core</span>
    </div>
    <ul class="sidebar-nav-list">
      <li class="sidebar-nav-item"><a href="#ch1" class="sidebar-nav-link">Chapter 1: Welcome to Cloud Studio</a></li>
      <li class="sidebar-nav-item"><a href="#ch2" class="sidebar-nav-link">Chapter 2: First 5 Minutes Tutorial</a></li>
      <li class="sidebar-nav-item"><a href="#ch3" class="sidebar-nav-link">Chapter 3: Login, Logout & Guest Mode</a></li>
      <li class="sidebar-nav-item"><a href="#ch4" class="sidebar-nav-link">Chapter 4: Understanding the Interface</a></li>
      <li class="sidebar-nav-item"><a href="#ch5" class="sidebar-nav-link">Chapter 5: Your First Notebook</a></li>
    </ul>
  </div>

  <!-- Category 2 -->
  <div class="sidebar-category">
    <div class="sidebar-category-header">
      <span>2. Writing & Running Python</span>
      <span class="badge badge-verified">Essential</span>
    </div>
    <ul class="sidebar-nav-list">
      <li class="sidebar-nav-item"><a href="#ch6" class="sidebar-nav-link">Chapter 6: How to Write Python Code</a></li>
      <li class="sidebar-nav-item"><a href="#ch7" class="sidebar-nav-link">Chapter 7: Executing Code & Controls</a></li>
      <li class="sidebar-nav-item"><a href="#ch8" class="sidebar-nav-link">Chapter 8: Understanding Output</a></li>
      <li class="sidebar-nav-item"><a href="#ch9" class="sidebar-nav-link">Chapter 9: Multi-Cell & Kernel State</a></li>
      <li class="sidebar-nav-item"><a href="#ch16" class="sidebar-nav-link">Chapter 16: Python Runtime & Kernel</a></li>
      <li class="sidebar-nav-item"><a href="#ch17" class="sidebar-nav-link">Chapter 17: Installing Packages (%pip)</a></li>
    </ul>
  </div>

  <!-- Category 3 -->
  <div class="sidebar-category">
    <div class="sidebar-category-header">
      <span>3. Data Science & Files</span>
      <span class="badge badge-verified">Analysis</span>
    </div>
    <ul class="sidebar-nav-list">
      <li class="sidebar-nav-item"><a href="#ch10" class="sidebar-nav-link">Chapter 10: NumPy & Pandas DataFrames</a></li>
      <li class="sidebar-nav-item"><a href="#ch11" class="sidebar-nav-link">Chapter 11: Charts & Visualizations</a></li>
      <li class="sidebar-nav-item"><a href="#ch12" class="sidebar-nav-link">Chapter 12: Uploading & Using Datasets</a></li>
    </ul>
  </div>

  <!-- Category 4 -->
  <div class="sidebar-category">
    <div class="sidebar-category-header">
      <span>4. Debugging & Troubleshooting</span>
      <span class="badge badge-verified">Diagnostics</span>
    </div>
    <ul class="sidebar-nav-list">
      <li class="sidebar-nav-item"><a href="#ch13" class="sidebar-nav-link">Chapter 13: Using the Python Debugger</a></li>
      <li class="sidebar-nav-item"><a href="#ch14" class="sidebar-nav-link">Chapter 14: Python Errors & How to Fix</a></li>
      <li class="sidebar-nav-item"><a href="#ch23" class="sidebar-nav-link">Chapter 23: AI Coding Assistant</a></li>
      <li class="sidebar-nav-item"><a href="#ch18" class="sidebar-nav-link">Chapter 18: Terminal & Shell Magics</a></li>
    </ul>
  </div>

  <!-- Category 5 -->
  <div class="sidebar-category">
    <div class="sidebar-category-header">
      <span>5. Organization & Settings</span>
      <span class="badge badge-verified">Workspace</span>
    </div>
    <ul class="sidebar-nav-list">
      <li class="sidebar-nav-item"><a href="#ch15" class="sidebar-nav-link">Chapter 15: Saving & Managing Work</a></li>
      <li class="sidebar-nav-item"><a href="#ch19" class="sidebar-nav-link">Chapter 19: Profile, Secrets & Themes</a></li>
      <li class="sidebar-nav-item"><a href="#ch20" class="sidebar-nav-link">Chapter 20: Sharing & Collaboration</a></li>
      <li class="sidebar-nav-item"><a href="#ch21" class="sidebar-nav-link">Chapter 21: Student Features</a></li>
      <li class="sidebar-nav-item"><a href="#ch22" class="sidebar-nav-link">Chapter 22: Instructor & Admin Console</a></li>
    </ul>
  </div>

  <!-- Category 6 -->
  <div class="sidebar-category">
    <div class="sidebar-category-header">
      <span>6. Beginner Tutorials (A–J)</span>
      <span class="badge badge-tutorial">Practice</span>
    </div>
    <ul class="sidebar-nav-list">
      <li class="sidebar-nav-item"><a href="#tut-a" class="sidebar-nav-link">Tutorial A: Hello World</a></li>
      <li class="sidebar-nav-item"><a href="#tut-b" class="sidebar-nav-link">Tutorial B: Simple Calculator</a></li>
      <li class="sidebar-nav-item"><a href="#tut-c" class="sidebar-nav-link">Tutorial C: Variables & State</a></li>
      <li class="sidebar-nav-item"><a href="#tut-d" class="sidebar-nav-link">Tutorial D: Interactive Pandas Table</a></li>
      <li class="sidebar-nav-item"><a href="#tut-e" class="sidebar-nav-link">Tutorial E: CSV Upload & Analysis</a></li>
      <li class="sidebar-nav-item"><a href="#tut-f" class="sidebar-nav-link">Tutorial F: Matplotlib Chart</a></li>
      <li class="sidebar-nav-item"><a href="#tut-g" class="sidebar-nav-link">Tutorial G: Find & Fix Syntax Error</a></li>
      <li class="sidebar-nav-item"><a href="#tut-h" class="sidebar-nav-link">Tutorial H: Debugging a Function</a></li>
      <li class="sidebar-nav-item"><a href="#tut-i" class="sidebar-nav-link">Tutorial I: Save & Download Work</a></li>
      <li class="sidebar-nav-item"><a href="#tut-j" class="sidebar-nav-link">Tutorial J: Multi-Cell Calculations</a></li>
    </ul>
  </div>

  <!-- Category 7 -->
  <div class="sidebar-category">
    <div class="sidebar-category-header">
      <span>7. Reference & Help</span>
      <span class="badge badge-verified">Quick Help</span>
    </div>
    <ul class="sidebar-nav-list">
      <li class="sidebar-nav-item"><a href="#ch24" class="sidebar-nav-link">Chapter 24: Keyboard Shortcuts</a></li>
      <li class="sidebar-nav-item"><a href="#ch25" class="sidebar-nav-link">Chapter 25: Troubleshooting KB</a></li>
      <li class="sidebar-nav-item"><a href="#ch26" class="sidebar-nav-link">Chapter 26: Frequently Asked Questions</a></li>
      <li class="sidebar-nav-item"><a href="#ch27" class="sidebar-nav-link">Chapter 27: Quick Start Cheat Sheet</a></li>
      <li class="sidebar-nav-item"><a href="#ch28" class="sidebar-nav-link">Chapter 28: Comprehensive Glossary</a></li>
    </ul>
  </div>

</aside>
"""

