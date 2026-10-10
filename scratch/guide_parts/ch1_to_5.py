"""
Chapters 1 through 5 for Python Cloud Studio User Guide.
"""

def get_chapters_1_to_5():
    return """
<!-- ========================================================================= -->
<!-- CHAPTER 1: Welcome to Python Cloud Studio -->
<!-- ========================================================================= -->
<section id="ch1" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 1</span>
      <span class="section-reading-time">3 min read</span>
    </div>
    <h2 class="section-title">Welcome to Python Cloud Studio</h2>
    <p class="section-lead">
      Learn what Python Cloud Studio is, why it eliminates traditional Python configuration headaches, and how it compares to local Jupyter and Google Colab.
    </p>
  </div>

  <div class="content-block">
    <h3>What is Python Cloud Studio?</h3>
    <p>
      <strong>Python Cloud Studio</strong> is a modern, enterprise-grade cloud workspace for writing, executing, and sharing Python code.
      Unlike traditional Python workflows that require installing Python interpreters, configuring <code>virtualenv</code> or Anaconda, and debugging environment path collisions on your local computer, Python Cloud Studio runs entirely inside your web browser.
    </p>
    <p>
      Under the hood, Python Cloud Studio pairs a high-performance frontend editor powered by Monaco (the engine behind Visual Studio Code) with a containerized Python kernel communicating over high-speed ZeroMQ and WebSocket connections.
    </p>

    <div class="callout callout-info">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        Why Browser-Based Cloud Execution Matters
      </div>
      <div class="callout-body">
        <p>Traditional local Python setups frequently break due to conflicting C-libraries, missing dependencies, or OS permission limits. With Python Cloud Studio:</p>
        <ul>
          <li><strong>Zero Local Installation:</strong> Open your browser to <code>http://localhost:8765</code> (or your organization's URL) and start coding instantly.</li>
          <li><strong>Consistent Hardware & Environment:</strong> Every session runs with a verified Python runtime, pre-configured data science libraries, and allocated system resources.</li>
          <li><strong>Cross-Platform Parity:</strong> Windows, macOS, Linux, and Chromebook users receive the exact same intuitive interface and execution environment.</li>
        </ul>
      </div>
    </div>

    <h3>How Python Cloud Studio Compares to Other Tools</h3>
    <table class="comparison-table">
      <thead>
        <tr>
          <th>Capability</th>
          <th>Python Cloud Studio</th>
          <th>Traditional Jupyter Lab</th>
          <th>Google Colab</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Setup Time</strong></td>
          <td><span class="badge badge-verified">Instant (0 sec)</span></td>
          <td>Requires Terminal, pip, conda (10-30 min)</td>
          <td>Instant with Google Account</td>
        </tr>
        <tr>
          <td><strong>Multi-Tenant Isolation</strong></td>
          <td><span class="badge badge-verified">Strict Tenant & Guest Sandbox</span></td>
          <td>Single-user / Local file access only</td>
          <td>Single Google Drive boundary</td>
        </tr>
        <tr>
          <td><strong>Pandas Table Viewer</strong></td>
          <td><span class="badge badge-verified">Interactive DataTableView (Filter, Sort, Export)</span></td>
          <td>Static HTML table</td>
          <td>Basic interactive filter (extension required)</td>
        </tr>
        <tr>
          <td><strong>Autocomplete & Signature Help</strong></td>
          <td><span class="badge badge-verified">Monaco Engine + Viewport-Aware Dropdowns</span></td>
          <td>Standard CodeMirror completions</td>
          <td>Custom autocomplete popup</td>
        </tr>
        <tr>
          <td><strong>Institutional / LMS Integration</strong></td>
          <td><span class="badge badge-verified">Built-in Classrooms & SuperAdmin Console</span></td>
          <td>Requires JupyterHub setup</td>
          <td>No native classroom gradebook</td>
        </tr>
      </tbody>
    </table>

    <div class="callout callout-tip">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>
        Who Is This Guide For?
      </div>
      <div class="callout-body">
        This documentation is designed for both <strong>complete beginners</strong> writing their very first line of code and <strong>data science professionals</strong> analyzing complex datasets. Each section includes clear visual explanations, practical code examples, and keyboard shortcuts.
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 2: First 5 Minutes Tutorial -->
<!-- ========================================================================= -->
<section id="ch2" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Chapter 2</span>
      <span class="section-reading-time">5 min practice</span>
    </div>
    <h2 class="section-title">First 5 Minutes Tutorial: Zero to Running Code</h2>
    <p class="section-lead">
      Follow this fast-track guide to launch Python Cloud Studio, write your first code cell, execute it, and see your output in under five minutes.
    </p>
  </div>

  <div class="content-block">
    <div class="step-card">
      <div class="step-num">1</div>
      <div class="step-content">
        <h4>Open the Application in Your Browser</h4>
        <p>Navigate to <code>http://localhost:8765</code> (or the web address provided by your administrator). The Studio opens immediately in <strong>Guest Mode</strong>, with a clean workspace ready for coding.</p>
        <p>Notice the top navigation bar displays <span class="badge badge-guest">Guest Mode — Public Workspace</span> and the kernel indicator shows <span class="badge badge-idle">Python 3 (idle)</span>.</p>
      </div>
    </div>

    <div class="step-card">
      <div class="step-num">2</div>
      <div class="step-content">
        <h4>Locate the Active Code Cell</h4>
        <p>In the central notebook area, you will see a rectangular block bordered in subtle gray with a left gutter showing <code>[ ]</code> and a circular <kbd>▶</kbd> Run button. This is a <strong>Code Cell</strong>.</p>
        <p>Click inside the dark editor box to place your cursor. A thin colored border highlights the active cell.</p>
      </div>
    </div>

    <div class="step-card">
      <div class="step-num">3</div>
      <div class="step-content">
        <h4>Type Your First Python Command</h4>
        <p>Type the following greeting code inside the cell:</p>
        <div class="code-container">
          <div class="code-header">
            <span class="code-lang">Python</span>
            <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
          </div>
          <pre class="code-pre"><code>name = "Python Explorer"
greeting = f"Welcome to Python Cloud Studio, {name}!"
print(greeting)</code></pre>
        </div>
      </div>
    </div>

    <div class="step-card">
      <div class="step-num">4</div>
      <div class="step-content">
        <h4>Execute the Cell</h4>
        <p>To run your code, you have two options:</p>
        <ul>
          <li><strong>Mouse:</strong> Click the circular <kbd>▶</kbd> button on the left gutter of the code cell.</li>
          <li><strong>Keyboard (Recommended):</strong> Press <kbd>Shift</kbd> + <kbd>Enter</kbd> (or <kbd>Ctrl</kbd> + <kbd>Enter</kbd>).</li>
        </ul>
        <p>While executing, the gutter button shows a spinning indicator. Within milliseconds, the execution counter changes to <code>[1]</code> and your output appears directly below the cell:</p>
        <div class="output-preview">
          <div class="output-header">Output [1]</div>
          <pre class="output-body">Welcome to Python Cloud Studio, Python Explorer!</pre>
        </div>
      </div>
    </div>

    <div class="step-card">
      <div class="step-num">5</div>
      <div class="step-content">
        <h4>Add a Second Cell and Reuse Variables</h4>
        <p>Click the <strong>+ Code</strong> button on the notebook toolbar or press <kbd>Alt</kbd> + <kbd>Enter</kbd> in your first cell. In the new cell, type:</p>
        <div class="code-container">
          <div class="code-header">
            <span class="code-lang">Python</span>
            <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
          </div>
          <pre class="code-pre"><code># Notice that 'name' is remembered from the previous cell!
print(f"Character count in your name: {len(name)}")</code></pre>
        </div>
        <p>Press <kbd>Shift</kbd> + <kbd>Enter</kbd> to run it. You have successfully created, connected, and executed your first multi-cell notebook!</p>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 3: Logging In, Logging Out, and Guest Mode -->
<!-- ========================================================================= -->
<section id="ch3" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 3</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Logging In, Logging Out, and Guest Mode</h2>
    <p class="section-lead">
      Understand how workspace isolation works, the difference between Public Guest Mode and Private Tenant Workspaces, and how your data remains strictly protected.
    </p>
  </div>

  <div class="content-block">
    <h3>The Two Workspace Modes</h3>
    <p>
      Python Cloud Studio provides a dual-tier workspace architecture designed for both friction-free experimentation and high-security enterprise isolation:
    </p>

    <div class="two-column-grid">
      <div class="feature-card">
        <div class="feature-card-header">
          <span class="badge badge-guest">Guest Mode (Public Workspace)</span>
        </div>
        <h4>Instant Collaboration Sandbox</h4>
        <ul>
          <li><strong>No Login Required:</strong> Anyone who opens the application starts here immediately.</li>
          <li><strong>Shared File Access:</strong> Files uploaded or created in Guest Mode live in <code>storage/workspaces/public/</code>.</li>
          <li><strong>Capability Tokens:</strong> Your browser receives an <code>X-Guest-Token</code> to track your temporary session.</li>
          <li><strong>Ideal For:</strong> Quick code testing, temporary calculations, and public classroom demonstrations.</li>
        </ul>
      </div>

      <div class="feature-card">
        <div class="feature-card-header">
          <span class="badge badge-verified">Authenticated (Private Workspace)</span>
        </div>
        <h4>Isolated Multi-Tenant Security</h4>
        <ul>
          <li><strong>Secured by JWT Authentication:</strong> Accessible only after logging in with your email and password.</li>
          <li><strong>Strict Tenant Isolation:</strong> Stored in <code>storage/workspaces/user_{id}/default/</code>. No other user can view or alter your files.</li>
          <li><strong>Persistent Storage:</strong> Your notebooks, CSV datasets, and environment secrets remain saved indefinitely.</li>
          <li><strong>SuperAdmin Oversight:</strong> Instructors and administrators can audit and manage workspaces without compromising tenant privacy.</li>
        </ul>
      </div>
    </div>

    <h3>How to Log In</h3>
    <ol>
      <li>Click the <strong>Sign In</strong> button located at the top-right corner of the navigation bar.</li>
      <li>An authentication modal appears over your current screen.</li>
      <li>Enter your registered <strong>Email</strong> and <strong>Password</strong>, then click <strong>Sign In</strong>.</li>
      <li>If you are a new student or team member, click <strong>Create an account</strong>, enter your full name, email, desired password, and click <strong>Register</strong>.</li>
      <li>Upon successful authentication, the top navbar instantly updates to display your name and a green <span class="badge badge-verified">Signed In — Private Workspace</span> badge.</li>
    </ol>

    <div class="callout callout-warning">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        Important: What Happens When You Log Out?
      </div>
      <div class="callout-body">
        <p>
          When you click the red <strong>Sign out</strong> button in the top navbar:
        </p>
        <ul>
          <li>Your JWT session token is instantly destroyed from browser memory.</li>
          <li>All active file editor tabs and notebook handles associated with your private account are closed immediately.</li>
          <li>The left file explorer automatically switches back to the <strong>Public Workspace</strong>.</li>
          <li>Your private files are <strong>NEVER visible</strong> to anyone who uses the browser after you log out.</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 4: Understanding the Studio Interface -->
<!-- ========================================================================= -->
<section id="ch4" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 4</span>
      <span class="section-reading-time">6 min read</span>
    </div>
    <h2 class="section-title">Understanding the Studio Interface</h2>
    <p class="section-lead">
      An in-depth visual breakdown of every toolbar, sidebar, panel, and indicator across Python Cloud Studio.
    </p>
  </div>

  <div class="content-block">
    <p>
      Python Cloud Studio uses a cohesive, high-density layout inspired by Google Colab and Visual Studio Code. The interface is organized into five primary regions:
    </p>

    <!-- Visual Architecture Diagram of the App -->
    <div class="diagram-container">
      <div class="diagram-title">Python Cloud Studio — Layout Architecture</div>
      <div class="app-layout-wireframe">
        <!-- Top Navbar Wireframe -->
        <div class="wireframe-navbar">
          <div class="wf-nav-left">
            <span class="wf-logo">Python Cloud Studio</span>
            <span class="wf-badge">Workspace Badge</span>
          </div>
          <div class="wf-nav-center">
            <span class="wf-pill">Notebooks Modal</span>
            <span class="wf-pill">Run All</span>
            <span class="wf-pill">Restart Kernel</span>
            <span class="wf-pill">Kernel Status (idle)</span>
          </div>
          <div class="wf-nav-right">
            <span class="wf-pill">Secrets</span>
            <span class="wf-pill">Theme</span>
            <span class="wf-pill">User Profile / Sign In</span>
          </div>
        </div>

        <!-- Main Body Grid Wireframe -->
        <div class="wireframe-body">
          <!-- Left Sidebar -->
          <div class="wireframe-sidebar-left">
            <div class="wf-header">FILES EXPLORER</div>
            <div class="wf-actions">+ File | + Folder | Upload | Refresh</div>
            <div class="wf-tree">
              <div>📁 data/</div>
              <div>&nbsp;&nbsp;📄 sales.csv</div>
              <div>📄 analysis.ipynb</div>
              <div>📄 script.py</div>
            </div>
            <div class="wf-footer">[Public] or [Private]</div>
          </div>

          <!-- Central Notebook Canvas -->
          <div class="wireframe-editor-center">
            <div class="wf-notebook-header">
              <span class="wf-title">📓 Untitled.ipynb</span>
              <span class="wf-actions">+ Code | + Text | Save (Ctrl+S)</span>
            </div>
            <div class="wf-cell">
              <div class="wf-cell-gutter">[1] ▶</div>
              <div class="wf-cell-code">import pandas as pd<br>df = pd.read_csv('data/sales.csv')<br>df</div>
            </div>
            <div class="wf-cell-output">
              <div class="wf-table-bar">Interactive DataTableView (Sort, Filter, Download)</div>
              <div class="wf-table-grid">[Interactive Table Rows]</div>
            </div>
            <div class="wf-resize-handle">═ Drag to Resize Cell Height (80px - 800px) ═</div>
          </div>

          <!-- Right Collapsible Panel -->
          <div class="wireframe-panel-right">
            <div class="wf-tab-bar">Files | AI | Vars | Stats</div>
            <div class="wf-panel-content">
              <div><strong>Tabbed File Editor</strong></div>
              <div>Edit .py, .csv, .md side-by-side with unsaved dirty bullet ●</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <h3>Detailed Region Breakdown</h3>
    <div class="accordion-item">
      <div class="accordion-header">
        <h4>1. Top Navigation Bar (Navbar)</h4>
        <span class="badge badge-verified">Always Visible</span>
      </div>
      <div class="accordion-content">
        <ul>
          <li><strong>Brand & Workspace Badge:</strong> Shows the active mode (<span class="badge badge-guest">Guest Mode</span> or <span class="badge badge-verified">Private Workspace</span>).</li>
          <li><strong>Notebooks Button (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>):</strong> Opens the Notebooks Manager dialog to switch, download, duplicate, or delete notebooks.</li>
          <li><strong>Run All (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>):</strong> Sequentially executes all code cells from top to bottom.</li>
          <li><strong>Restart Kernel (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>):</strong> Wipes kernel memory and starts a fresh Python interpreter session. Rotates with an animation while restarting.</li>
          <li><strong>Kernel Status Pill:</strong> Live color-coded indicator:
            <ul>
              <li><span class="badge badge-idle">Python 3 (idle)</span> — Kernel is ready to receive commands.</li>
              <li><span class="badge badge-busy">Python 3 (busy)</span> — Currently executing code.</li>
              <li><span class="badge badge-restarting">Python 3 (restarting)</span> — Kernel process is rebooting.</li>
              <li><span class="badge badge-disconnected">Disconnected</span> — Network connection lost.</li>
            </ul>
          </li>
          <li><strong>Secrets (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="7.5" cy="15.5" r="5.5"></circle><path d="m21 2-9.6 9.6"></path><path d="m15.5 7.5 3 3L22 7l-3-3"></path></svg>):</strong> Configures workspace environment variables and API keys (e.g., OpenAI, Gemini, HuggingFace).</li>
          <li><strong>Theme Toggle:</strong> Switches seamlessly between System, Dark, and Light themes.</li>
        </ul>
      </div>
    </div>

    <div class="accordion-item">
      <div class="accordion-header">
        <h4>2. Left Sidebar (Files Explorer)</h4>
        <span class="badge badge-verified">Collapsible (Ctrl+B)</span>
      </div>
      <div class="accordion-content">
        <ul>
          <li><strong>Toolbar Actions:</strong> <code>+ File</code> creates a new file; <code>+ Folder</code> creates a subfolder; <code>Upload</code> uploads files from your computer; <code>Refresh</code> reloads the tree.</li>
          <li><strong>Drag-and-Drop:</strong> You can drag files directly from your computer's desktop into the sidebar to upload them.</li>
          <li><strong>Context Menu:</strong> Right-clicking any file or folder reveals: <em>Rename</em>, <em>Download</em>, and <em>Delete</em>.</li>
          <li><strong>Double-Click to Edit:</strong> Double-clicking any non-notebook file (like <code>.py</code>, <code>.csv</code>, <code>.txt</code>, <code>.md</code>) opens it directly in the Right Panel Tabbed Editor.</li>
        </ul>
      </div>
    </div>

    <div class="accordion-item">
      <div class="accordion-header">
        <h4>3. Central Notebook Canvas & Resizable Cells</h4>
        <span class="badge badge-verified">Core Work Area</span>
      </div>
      <div class="accordion-content">
        <ul>
          <li><strong>Code Cells:</strong> Monaco-based editor with syntax highlighting, line numbers, autocomplete, and diagnostics.</li>
          <li><strong>Execution Counter:</strong> Shows <code>[ ]</code> before execution and <code>[n]</code> after, displaying the order in which cells were run.</li>
          <li><strong>Drag-to-Resize Handle:</strong> Every code cell features an ergonomic drag handle at the bottom edge. Click and drag vertically to resize the editor height anywhere from <strong>80px to 800px</strong>. Cell heights are automatically saved in notebook metadata!</li>
        </ul>
      </div>
    </div>

    <div class="accordion-item">
      <div class="accordion-header">
        <h4>4. Right Side Panel</h4>
        <span class="badge badge-verified">Auxiliary Tools</span>
      </div>
      <div class="accordion-content">
        <ul>
          <li><strong>Files Tab:</strong> Tabbed editor for working with companion scripts, configuration files, or viewing raw CSV text.</li>
          <li><strong>AI Assistant Tab:</strong> Built-in intelligent programming assistant to generate code, explain errors, and insert snippets directly into your notebook.</li>
          <li><strong>Variables Tab:</strong> Inspect active Python variables stored in kernel memory.</li>
          <li><strong>Metrics Tab:</strong> Monitor real-time CPU, RAM, and Disk allocation.</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 5: Your First Notebook: Creation, Structure & Cells -->
<!-- ========================================================================= -->
<section id="ch5" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 5</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Your First Notebook: Creation, Structure & Cells</h2>
    <p class="section-lead">
      Learn how Jupyter notebooks are organized, how to create and rename notebooks, and the fundamental anatomy of code cells.
    </p>
  </div>

  <div class="content-block">
    <h3>What is a Jupyter Notebook (`.ipynb`)?</h3>
    <p>
      A notebook is an interactive computational document that combines runnable code, formatted text, equations, and rich visualizations into a single file. Under the hood, notebooks are saved in standard <strong>Jupyter Notebook Format v4</strong> (JSON structure), which means your work is 100% portable and can be opened in VS Code, JupyterLab, or Google Colab.
    </p>

    <h3>Creating and Managing Notebooks</h3>
    <p>You can create a new notebook in two simple ways:</p>
    <ul>
      <li>Click the <strong>Notebooks</strong> button in the top navbar and click <strong>+ New Notebook</strong>.</li>
      <li>Click the <strong>+ File</strong> button in the left sidebar and enter a filename ending with <code>.ipynb</code> (e.g., <code>data_analysis.ipynb</code>).</li>
    </ul>

    <h3>Cell Anatomy: Code vs. Markdown</h3>
    <div class="two-column-grid">
      <div class="feature-card">
        <h4>Code Cells</h4>
        <p>Used to write executable Python code. They feature:</p>
        <ul>
          <li>Left execution gutter with run button <kbd>▶</kbd></li>
          <li>Execution order number: <code>[1]</code>, <code>[2]</code>, etc.</li>
          <li>Output area below the editor for text, tables, and images.</li>
          <li>Monaco editor with full IntelliSense and diagnostics.</li>
        </ul>
      </div>
      <div class="feature-card">
        <h4>Markdown (Text) Cells</h4>
        <p>Used to document your work, explain methodology, and create headers:</p>
        <ul>
          <li>Supports standard Markdown: <code># Headers</code>, <code>**bold**</code>, <code>*italics*</code>.</li>
          <li>Rendered automatically when you click outside or press <kbd>Shift</kbd> + <kbd>Enter</kbd>.</li>
          <li>Supports lists, links, tables, and LaTeX math equations.</li>
        </ul>
      </div>
    </div>

    <h3>Cell Action Toolbar</h3>
    <p>When you hover over or select a cell, an action toolbar appears allowing you to:</p>
    <ul>
      <li><strong>Run Cell:</strong> Execute the cell immediately.</li>
      <li><strong>Move Up / Down:</strong> Reorder cells within the notebook document.</li>
      <li><strong>Duplicate Cell:</strong> Create an exact copy of the cell directly below.</li>
      <li><strong>Delete Cell:</strong> Remove the cell (with an undo safety buffer).</li>
    </ul>
  </div>
</section>
"""

