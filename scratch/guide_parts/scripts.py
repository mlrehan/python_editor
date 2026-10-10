"""
Client-side Vanilla JavaScript for Python Cloud Studio User Guide.
"""

def get_scripts():
    return """
<script>
(function() {
  'use strict';

  // --- 1. LOCAL SEARCH INDEX (28 Chapters + 10 Tutorials + Key Concepts) ---
  const searchIndex = [
    { title: "Chapter 1: Welcome to Python Cloud Studio", url: "#ch1", category: "Core", keywords: "cloud editor browser zero installation vscode monaco colab jupyter comparison" },
    { title: "Chapter 2: First 5 Minutes Tutorial", url: "#ch2", category: "Getting Started", keywords: "quickstart first code print run execute shift enter" },
    { title: "Chapter 3: Logging In, Logging Out, and Guest Mode", url: "#ch3", category: "Auth", keywords: "guest mode public workspace private workspace jwt authentication logout isolation security" },
    { title: "Chapter 4: Understanding the Studio Interface", url: "#ch4", category: "Interface", keywords: "navbar files sidebar right panel code cells drag handle status pill" },
    { title: "Chapter 5: Your First Notebook: Creation & Structure", url: "#ch5", category: "Notebooks", keywords: "ipynb new notebook cell markdown code gutter" },
    { title: "Chapter 6: How to Write Python Code & IntelliSense", url: "#ch6", category: "Editing", keywords: "monaco intellisense autocomplete signature help diagnostics squiggly dropdown suggestions tab enter" },
    { title: "Chapter 7: Executing Code & Execution Controls", url: "#ch7", category: "Execution", keywords: "run cell shift enter ctrl enter alt enter run all interrupt infinite loop" },
    { title: "Chapter 8: Understanding Output", url: "#ch8", category: "Output", keywords: "stdout print return value ansi tracebacks html rich output" },
    { title: "Chapter 9: Multi-Cell & Kernel State", url: "#ch9", category: "Kernel", keywords: "shared memory namespace out of order restart run all" },
    { title: "Chapter 10: NumPy & Pandas DataFrames (Interactive DataTableView)", url: "#ch10", category: "Data", keywords: "datatableview table pandas sort filter search pagination csv tsv export" },
    { title: "Chapter 11: Charts & Visualizations", url: "#ch11", category: "Charts", keywords: "matplotlib seaborn plot inline png figures" },
    { title: "Chapter 12: Uploading & Using Datasets", url: "#ch12", category: "Files", keywords: "upload dataset csv read_csv drag drop tabbed editor" },
    { title: "Chapter 13: Using the Python Debugger", url: "#ch13", category: "Debugging", keywords: "breakpoint pdb next step continue print variable dap" },
    { title: "Chapter 14: Python Errors & How to Fix Them", url: "#ch14", category: "Errors", keywords: "syntaxerror nameerror typeerror modulenotfounderror fix traceback" },
    { title: "Chapter 15: Saving & Managing Your Work", url: "#ch15", category: "Workspace", keywords: "save ctrl s notebooks modal download ipynb duplicate delete" },
    { title: "Chapter 16: Python Runtime & Kernel Management", url: "#ch16", category: "Runtime", keywords: "ipykernel zeromq restart status idle busy disconnected websocket" },
    { title: "Chapter 17: Installing Packages with %pip", url: "#ch17", category: "Packages", keywords: "pip install magic user site packages dynamic import sys path" },
    { title: "Chapter 18: Terminal & Shell Magics", url: "#ch18", category: "Shell", keywords: "shell bang commands time timeit who pty terminal" },
    { title: "Chapter 19: Profile, Secrets & Themes", url: "#ch19", category: "Settings", keywords: "secrets api key openai gemini env theme dark light system" },
    { title: "Chapter 20: Sharing & Collaboration", url: "#ch20", category: "Sharing", keywords: "share export collaborate classrooms public workspace" },
    { title: "Chapter 21: Student Features & Assignments", url: "#ch21", category: "Students", keywords: "classroom join code assignment autograding assert tests" },
    { title: "Chapter 22: Instructor & SuperAdmin Console", url: "#ch22", category: "Admin", keywords: "superadmin dashboard users packages audit logs runtimes" },
    { title: "Chapter 23: AI Coding Assistant", url: "#ch23", category: "AI", keywords: "ai assistant chat prompt code generator insert notebook" },
    { title: "Chapter 24: Keyboard Shortcuts Matrix", url: "#ch24", category: "Shortcuts", keywords: "keyboard shortcuts windows mac hotkeys table" },
    { title: "Chapter 25: Troubleshooting Knowledge Base", url: "#ch25", category: "Help", keywords: "troubleshooting kb disconnected hung loop sitecustomize" },
    { title: "Chapter 26: Frequently Asked Questions (FAQ)", url: "#ch26", category: "FAQ", keywords: "faq questions beginner answers installation saving" },
    { title: "Chapter 27: Quick Start Cheat Sheet", url: "#ch27", category: "Reference", keywords: "cheat sheet printable summary pandas matplotlib python" },
    { title: "Chapter 28: Comprehensive Glossary", url: "#ch28", category: "Glossary", keywords: "glossary definitions kernel zeromq monaco datatableview ast" },
    { title: "Tutorial A: Hello World & Modern String Formatting", url: "#tut-a", category: "Tutorial", keywords: "hello world f-strings datetime strings beginner" },
    { title: "Tutorial B: Simple Calculator & Numerical Types", url: "#tut-b", category: "Tutorial", keywords: "calculator math float int tax installment" },
    { title: "Tutorial C: Lists, Dictionaries, and Loops", url: "#tut-c", category: "Tutorial", keywords: "list dict dictionary for loop iteration grades" },
    { title: "Tutorial D: Interactive Pandas Table Exploration", url: "#tut-d", category: "Tutorial", keywords: "pandas datatableview sort search filter revenue" },
    { title: "Tutorial E: CSV Upload & Summary Statistics", url: "#tut-e", category: "Tutorial", keywords: "csv upload describe statistics metrics mean" },
    { title: "Tutorial F: Matplotlib Chart Creation", url: "#tut-f", category: "Tutorial", keywords: "matplotlib bar chart plot revenue figures" },
    { title: "Tutorial G: Find & Fix Syntax Error", url: "#tut-g", category: "Tutorial", keywords: "syntax error bracket colon squiggly fix" },
    { title: "Tutorial H: Debugging a Function with breakpoint()", url: "#tut-h", category: "Tutorial", keywords: "breakpoint debug pdb function inspect" },
    { title: "Tutorial I: Save & Download Your Work", url: "#tut-i", category: "Tutorial", keywords: "save download ipynb export notebook" },
    { title: "Tutorial J: End-to-End Multi-Cell Data Pipeline", url: "#tut-j", category: "Tutorial", keywords: "pipeline multi cell data transform chart" }
  ];

  // --- 2. SEARCH MODAL LOGIC ---
  const searchModal = document.getElementById('searchModalBackdrop');
  const searchInput = document.getElementById('searchModalInput');
  const searchResults = document.getElementById('searchResultsList');
  const openSearchBtn = document.getElementById('openSearchBtn');
  const closeSearchBtn = document.getElementById('closeSearchModalBtn');
  let selectedSearchIndex = -1;

  function openSearch() {
    if (!searchModal) return;
    searchModal.classList.add('open');
    searchInput.value = '';
    renderSearchResults('');
    setTimeout(() => searchInput.focus(), 50);
  }

  function closeSearch() {
    if (!searchModal) return;
    searchModal.classList.remove('open');
    selectedSearchIndex = -1;
  }

  function renderSearchResults(query) {
    if (!searchResults) return;
    const q = query.trim().toLowerCase();
    let matches = [];

    if (!q) {
      matches = searchIndex.slice(0, 8); // show popular initial items
    } else {
      matches = searchIndex.filter(item => {
        return item.title.toLowerCase().includes(q) ||
               item.keywords.toLowerCase().includes(q) ||
               item.category.toLowerCase().includes(q);
      });
    }

    if (matches.length === 0) {
      searchResults.innerHTML = '<li class="no-results">No matching guides or tutorials found for "' + escapeHtml(q) + '".</li>';
      selectedSearchIndex = -1;
      return;
    }

    searchResults.innerHTML = matches.map((item, idx) => `
      <li class="search-result-item ${idx === 0 ? 'highlighted' : ''}" data-url="${item.url}">
        <div class="result-title">${escapeHtml(item.title)}</div>
        <div class="result-meta">
          <span class="result-badge">${escapeHtml(item.category)}</span>
          <span class="result-url">${item.url}</span>
        </div>
      </li>
    `).join('');

    selectedSearchIndex = 0;

    // Attach click events
    searchResults.querySelectorAll('.search-result-item').forEach(item => {
      item.addEventListener('click', () => {
        const url = item.getAttribute('data-url');
        if (url) {
          closeSearch();
          window.location.hash = url;
        }
      });
    });
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  if (openSearchBtn) openSearchBtn.addEventListener('click', openSearch);
  if (closeSearchBtn) closeSearchBtn.addEventListener('click', closeSearch);
  if (searchModal) {
    searchModal.addEventListener('click', (e) => {
      if (e.target === searchModal) closeSearch();
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => renderSearchResults(e.target.value));
    searchInput.addEventListener('keydown', (e) => {
      const items = searchResults.querySelectorAll('.search-result-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (items.length > 0) {
          selectedSearchIndex = (selectedSearchIndex + 1) % items.length;
          updateHighlightedSearchItem(items);
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (items.length > 0) {
          selectedSearchIndex = (selectedSearchIndex - 1 + items.length) % items.length;
          updateHighlightedSearchItem(items);
        }
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (items.length > 0 && selectedSearchIndex >= 0 && items[selectedSearchIndex]) {
          const url = items[selectedSearchIndex].getAttribute('data-url');
          if (url) {
            closeSearch();
            window.location.hash = url;
          }
        }
      } else if (e.key === 'Escape') {
        closeSearch();
      }
    });
  }

  function updateHighlightedSearchItem(items) {
    items.forEach((item, idx) => {
      if (idx === selectedSearchIndex) {
        item.classList.add('highlighted');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('highlighted');
      }
    });
  }

  // Global search hotkeys (Ctrl+K, Cmd+K, /)
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      openSearch();
    } else if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault();
      openSearch();
    }
  });


  // --- 3. THEME TOGGLE (System / Dark / Light) ---
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIconSun = document.getElementById('themeIconSun');
  const themeIconMoon = document.getElementById('themeIconMoon');
  const themeLabel = document.getElementById('themeLabel');

  function initTheme() {
    const savedTheme = localStorage.getItem('pcs_guide_theme') || 'dark';
    applyTheme(savedTheme);
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('pcs_guide_theme', theme);

    if (theme === 'light') {
      if (themeIconSun) themeIconSun.style.display = 'none';
      if (themeIconMoon) themeIconMoon.style.display = 'inline-block';
      if (themeLabel) themeLabel.textContent = 'Light';
    } else {
      if (themeIconSun) themeIconSun.style.display = 'inline-block';
      if (themeIconMoon) themeIconMoon.style.display = 'none';
      if (themeLabel) themeLabel.textContent = 'Dark';
    }
  }

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
    });
  }

  initTheme();


  // --- 4. CLIPBOARD COPY WITH FILE:// RESTRICTION FALLBACK ---
  window.copySnippet = function(button) {
    const container = button.closest('.code-container');
    if (!container) return;
    const codePre = container.querySelector('code');
    if (!codePre) return;
    const textToCopy = codePre.innerText || codePre.textContent;

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(textToCopy).then(() => {
        showCopySuccess(button);
      }).catch(() => {
        fallbackCopy(textToCopy, button);
      });
    } else {
      fallbackCopy(textToCopy, button);
    }
  };

  function fallbackCopy(text, button) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    textArea.style.top = '-9999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      showCopySuccess(button);
    } catch (err) {
      button.textContent = 'Failed';
      setTimeout(() => { button.textContent = 'Copy'; }, 2000);
    }
    document.body.removeChild(textArea);
  }

  function showCopySuccess(button) {
    const originalText = button.textContent;
    button.textContent = '✔ Copied!';
    button.classList.add('copied');
    setTimeout(() => {
      button.textContent = originalText;
      button.classList.remove('copied');
    }, 2000);
  }


  // --- 5. PRINT TRIGGER ---
  const printDocBtn = document.getElementById('printDocBtn');
  if (printDocBtn) {
    printDocBtn.addEventListener('click', () => window.print());
  }


  // --- 6. MOBILE MENU TOGGLE ---
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const docsSidebar = document.getElementById('docsSidebar');

  if (mobileMenuBtn && docsSidebar) {
    mobileMenuBtn.addEventListener('click', () => {
      docsSidebar.classList.toggle('open');
    });

    // Close when clicking any nav link on mobile
    docsSidebar.querySelectorAll('.sidebar-nav-link').forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 1024) {
          docsSidebar.classList.remove('open');
        }
      });
    });
  }


  // --- 7. READING PROGRESS BAR & SCROLLSPY ---
  const progressBar = document.getElementById('readingProgress');
  const navLinks = document.querySelectorAll('.sidebar-nav-link');
  const sections = document.querySelectorAll('.docs-section');

  window.addEventListener('scroll', () => {
    // Progress Bar
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    if (progressBar && docHeight > 0) {
      const progressPercent = (scrollTop / docHeight) * 100;
      progressBar.style.width = progressPercent + '%';
    }

    // Scrollspy Highlight
    let currentSectionId = '';
    sections.forEach(section => {
      const rect = section.getBoundingClientRect();
      if (rect.top <= 140 && rect.bottom >= 140) {
        currentSectionId = section.getAttribute('id');
      }
    });

    if (currentSectionId) {
      navLinks.forEach(link => {
        if (link.getAttribute('href') === '#' + currentSectionId) {
          link.classList.add('active');
        } else {
          link.classList.remove('active');
        }
      });
    }
  });

})();
</script>
"""

