"""
Chapters 15 through 20 for Python Cloud Studio User Guide.
"""

def get_chapters_15_to_20():
    return """
<!-- ========================================================================= -->
<!-- CHAPTER 15: Saving & Managing Your Work -->
<!-- ========================================================================= -->
<section id="ch15" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 15</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Saving & Managing Your Work</h2>
    <p class="section-lead">
      Learn how to save notebooks, download `.ipynb` files to your computer, duplicate templates, and organize workspace files.
    </p>
  </div>

  <div class="content-block">
    <h3>Saving Notebooks (`Ctrl+S`)</h3>
    <p>
      Whenever you edit code or generate new cell outputs, press <kbd>Ctrl</kbd> + <kbd>S</kbd> (or <kbd>⌘</kbd> + <kbd>S</kbd> on macOS).
      A toast notification confirms the save, and the file is written to your workspace storage in valid Jupyter Notebook format v4 JSON.
    </p>

    <h3>Using the Notebooks Manager Modal</h3>
    <p>
      Click the <strong>Notebooks</strong> button (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>) in the top navbar to open the comprehensive <strong>Notebooks Management Dialog</strong>:
    </p>

    <table class="comparison-table">
      <thead>
        <tr>
          <th>Action</th>
          <th>Button</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Switch Active</strong></td>
          <td>Click Notebook Card</td>
          <td>Switches your active editor canvas to the selected notebook without page reload.</td>
        </tr>
        <tr>
          <td><strong>Download</strong></td>
          <td><kbd>Download .ipynb</kbd></td>
          <td>Downloads the raw notebook directly to your computer's Downloads folder.</td>
        </tr>
        <tr>
          <td><strong>Duplicate</strong></td>
          <td><kbd>Duplicate</kbd></td>
          <td>Creates an exact clone of the notebook (e.g., <code>analysis_copy.ipynb</code>) for safe experimentation.</td>
        </tr>
        <tr>
          <td><strong>Delete</strong></td>
          <td><kbd>Delete</kbd></td>
          <td>Deletes the notebook after a confirmation prompt.</td>
        </tr>
      </tbody>
    </table>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 16: Python Runtime & Kernel Management -->
<!-- ========================================================================= -->
<section id="ch16" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 16</span>
      <span class="section-reading-time">5 min read</span>
    </div>
    <h2 class="section-title">Python Runtime & Kernel Management</h2>
    <p class="section-lead">
      Understand the underlying IPyKernel architecture, how ZeroMQ channels handle code execution, and how to safely reboot the runtime.
    </p>
  </div>

  <div class="content-block">
    <h3>Kernel Architecture & Execution Pipeline</h3>
    <p>
      When you click Run or press <kbd>Shift</kbd> + <kbd>Enter</kbd>, your browser does not execute Python directly. Instead:
    </p>
    <ol>
      <li>The code string is packaged into a JSON execution message and sent via WebSocket to the FastAPI backend.</li>
      <li>The backend relays the request through high-performance ZeroMQ sockets to an isolated <strong>IPyKernel</strong> process.</li>
      <li>Output streams (stdout, stderr, display_data) stream back in real-time to your notebook canvas.</li>
    </ol>

    <!-- Visual Architecture of the Kernel Lifecycle -->
    <div class="diagram-container">
      <div class="diagram-title">ZeroMQ & IPyKernel Execution Flow</div>
      <div class="state-diagram-wrapper">
        <div class="cell-node">
          <div class="node-title">Monaco Editor</div>
          <div class="node-code">User presses Shift+Enter</div>
        </div>
        <div class="node-arrow">── WebSocket ──▶</div>
        <div class="kernel-node">
          <div class="kernel-title">FastAPI Backend (8765)</div>
          <div class="kernel-vars">Dispatches via ZeroMQ</div>
        </div>
        <div class="node-arrow">── ZeroMQ ──▶</div>
        <div class="cell-node">
          <div class="node-title">Python IPyKernel</div>
          <div class="node-code">Executes in Sandbox</div>
        </div>
      </div>
    </div>

    <h3>Restarting the Kernel</h3>
    <p>
      If your kernel becomes unresponsive or you want to wipe all variables from memory to start fresh:
    </p>
    <ol>
      <li>Click the <strong>Restart</strong> button (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>) in the top navbar.</li>
      <li>The icon spins (<code>animate-spin</code>) and the status pill turns pulsing blue (<span class="badge badge-restarting">restarting</span>).</li>
      <li>A toast banner announces <em>"Kernel restarted successfully"</em>.</li>
      <li>All active variables are wiped, and diagnostics refresh automatically.</li>
    </ol>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 17: Installing Packages with %pip -->
<!-- ========================================================================= -->
<section id="ch17" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 17</span>
      <span class="section-reading-time">5 min read</span>
    </div>
    <h2 class="section-title">Installing Packages with %pip</h2>
    <p class="section-lead">
      Learn how to install third-party Python libraries using magic commands, understand isolated user site-packages, and why restart is no longer required.
    </p>
  </div>

  <div class="content-block">
    <h3>Installing Libraries Directly in a Code Cell</h3>
    <p>
      Need a package that isn't pre-installed? You can install it on-the-fly directly inside your notebook using the standard <code>%pip</code> magic command:
    </p>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code># Install any PyPI package into your workspace
%pip install rich polars scikit-learn</code></pre>
    </div>

    <div class="callout callout-info">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        How Python Cloud Studio Protects the System Environment
      </div>
      <div class="callout-body">
        <ul>
          <li><strong>Automatic User Isolation:</strong> When you run <code>%pip install</code>, Cloud Studio automatically injects <code>--user</code> behind the scenes. Packages are placed into your personal <code>.local/lib/python3.x/site-packages</code>.</li>
          <li><strong>No Kernel Restart Needed:</strong> Cloud Studio immediately invalidates Python's <code>sys.path_importer_cache</code>. You can import your newly installed library in the very next cell without restarting the kernel!</li>
          <li><strong>Guest Protection:</strong> Guest accounts are restricted from altering the system environment. Sign in to install custom libraries.</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 18: Terminal & Shell Magics -->
<!-- ========================================================================= -->
<section id="ch18" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 18</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Terminal & Shell Magics</h2>
    <p class="section-lead">
      Execute operating system shell commands safely using the `!` prefix, run IPython line magics, and understand security restrictions.
    </p>
  </div>

  <div class="content-block">
    <div class="callout callout-info">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        Current Shell Workflow & Web PTY Roadmap
      </div>
      <div class="callout-body">
        In the current release, command-line operations run through safe IPython cell execution (using <code>!</code> and <code>%</code>). An embedded, full-featured web terminal (PTY / xterm.js) is on our development roadmap for enterprise deployment.
      </div>
    </div>

    <h3>Running Shell Commands with `!`</h3>
    <p>Prefix any line in a code cell with an exclamation mark (<code>!</code>) to execute it in the underlying operating system environment:</p>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Bash</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code># Inspect files in the current workspace directory
!dir

# Check active Python interpreter version
!python --version</code></pre>
    </div>

    <h3>Common IPython Magics</h3>
    <table class="comparison-table">
      <thead>
        <tr>
          <th>Magic</th>
          <th>Purpose</th>
          <th>Example</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>%time</code></td>
          <td>Measures execution time of a single statement.</td>
          <td><code>%time sum(range(1000000))</code></td>
        </tr>
        <tr>
          <td><code>%timeit</code></td>
          <td>Runs code multiple times to compute average benchmark.</td>
          <td><code>%timeit [x**2 for x in range(1000)]</code></td>
        </tr>
        <tr>
          <td><code>%who</code></td>
          <td>Lists all defined variables in the kernel namespace.</td>
          <td><code>%who</code></td>
        </tr>
        <tr>
          <td><code>%pip</code></td>
          <td>Installs packages into user site-packages.</td>
          <td><code>%pip install rich</code></td>
        </tr>
      </tbody>
    </table>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 19: Profile, Secrets & Themes -->
<!-- ========================================================================= -->
<section id="ch19" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 19</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Profile, Secrets & Themes</h2>
    <p class="section-lead">
      Manage API keys with the Secrets Modal, configure environment variables, and switch between System, Dark, and Light visual themes.
    </p>
  </div>

  <div class="content-block">
    <h3>Managing API Keys with SecretsModal</h3>
    <p>
      Never hardcode sensitive API keys or database passwords in your notebook code! Python Cloud Studio includes a dedicated <strong>Secrets Manager</strong>:
    </p>
    <ol>
      <li>Click the <strong>Secrets</strong> button (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="7.5" cy="15.5" r="5.5"></circle><path d="m21 2-9.6 9.6"></path><path d="m15.5 7.5 3 3L22 7l-3-3"></path></svg>) in the top navbar.</li>
      <li>Choose from preset templates (<code>OPENAI_API_KEY</code>, <code>GEMINI_API_KEY</code>, <code>ANTHROPIC_API_KEY</code>, <code>HUGGINGFACE_API_KEY</code>) or click <strong>+ Add Custom Secret</strong>.</li>
      <li>Secrets are stored securely in your private workspace <code>.env</code> file and automatically injected into Python's <code>os.environ</code>.</li>
    </ol>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>import os

# Safely read secrets from environment variables
api_key = os.environ.get("OPENAI_API_KEY")
print("Key configured:", bool(api_key))</code></pre>
    </div>

    <h3>Switching Visual Themes</h3>
    <p>
      Click the <strong>Theme</strong> dropdown in the top navbar to choose:
    </p>
    <ul>
      <li><strong>System:</strong> Automatically matches your operating system's light or dark mode setting.</li>
      <li><strong>Dark:</strong> High-contrast modern dark palette engineered for low eye fatigue.</li>
      <li><strong>Light:</strong> Crisp, clean high-contrast light theme ideal for classroom presentations and daytime work.</li>
    </ul>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 20: Sharing & Collaboration -->
<!-- ========================================================================= -->
<section id="ch20" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 20</span>
      <span class="section-reading-time">3 min read</span>
    </div>
    <h2 class="section-title">Sharing & Collaboration</h2>
    <p class="section-lead">
      Export your notebooks for colleagues, share analysis via the Public Workspace, and present findings cleanly.
    </p>
  </div>

  <div class="content-block">
    <h3>Ways to Share Your Work</h3>
    <div class="three-column-grid">
      <div class="feature-card">
        <h4>1. Export as `.ipynb`</h4>
        <p>In the Notebooks Modal, click <strong>Download .ipynb</strong>. The file can be uploaded to GitHub, emailed to colleagues, or imported into Google Colab.</p>
      </div>
      <div class="feature-card">
        <h4>2. Public Workspace Sharing</h4>
        <p>Save or copy a notebook into the Public Workspace to make it immediately viewable and runnable by students and team guests.</p>
      </div>
      <div class="feature-card">
        <h4>3. Classroom Assignments</h4>
        <p>Instructors can publish assignment templates to classrooms where students can complete and submit their solutions.</p>
      </div>
    </div>
  </div>
</section>
"""

