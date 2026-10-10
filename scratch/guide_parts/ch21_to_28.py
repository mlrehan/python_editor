"""
Chapters 21 through 28 for Python Cloud Studio User Guide.
"""

def get_chapters_21_to_28():
    return """
<!-- ========================================================================= -->
<!-- CHAPTER 21: Student Features -->
<!-- ========================================================================= -->
<section id="ch21" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 21</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Student Features & Assignments</h2>
    <p class="section-lead">
      How students join classrooms, complete coding assignments, run automated test cells, and submit their coursework.
    </p>
  </div>

  <div class="content-block">
    <h3>Joining a Classroom</h3>
    <p>
      Instructors provide an enrollment join code (e.g., <code>CS101-FALL</code>). When enrolled as a student:
    </p>
    <ol>
      <li>Sign in to your private account using your student email.</li>
      <li>Assignments appear in your workspace under the <code>assignments/</code> directory.</li>
      <li>Open the assigned <code>.ipynb</code> notebook to begin your coursework.</li>
    </ol>

    <h3>Working with Autograded Test Cells</h3>
    <p>
      Many courses include validation cells containing <code>assert</code> statements:
    </p>
    <div class="code-container">
      <div class="code-header"><span class="code-lang">Python</span></div>
      <pre class="code-pre"><code># Exercise: Define a function 'celsius_to_fahrenheit'
def celsius_to_fahrenheit(c):
    return (c * 9/5) + 32

# Automated Test Cell:
assert celsius_to_fahrenheit(0) == 32.0, "Test failed for 0°C"
assert celsius_to_fahrenheit(100) == 212.0, "Test failed for 100°C"
print("✔ All tests passed!")</code></pre>
    </div>
    <p>If all <code>assert</code> statements execute without an <code>AssertionError</code>, your solution is verified!</p>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 22: Instructor & SuperAdmin Console -->
<!-- ========================================================================= -->
<section id="ch22" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 22</span>
      <span class="section-reading-time">5 min read</span>
    </div>
    <h2 class="section-title">Instructor & SuperAdmin Console</h2>
    <p class="section-lead">
      Comprehensive administration guide for managing users, installing system-wide packages, auditing workspaces, and reviewing security logs.
    </p>
  </div>

  <div class="content-block">
    <p>
      Users with <code>super_admin</code> or <code>admin</code> roles see an amber shield <strong>Admin</strong> button in the top navbar. Clicking it opens the <strong>SuperAdmin Dashboard</strong>:
    </p>

    <!-- SuperAdmin Tabs Grid -->
    <div class="two-column-grid">
      <div class="feature-card">
        <h4>1. System Overview</h4>
        <p>Live health metrics, active kernel process counts, memory utilization, and real-time user session activity.</p>
      </div>
      <div class="feature-card">
        <h4>2. User & Role Management</h4>
        <p>Manage users, assign roles (<code>student</code>, <code>instructor</code>, <code>admin</code>), suspend accounts, or reset user access.</p>
      </div>
      <div class="feature-card">
        <h4>3. System Packages Manager</h4>
        <p>Install or uninstall Python packages across the entire server environment with authorized package governance.</p>
      </div>
      <div class="feature-card">
        <h4>4. Workspaces & File Audit</h4>
        <p>Inspect tenant file trees, check quota allocations, and enforce organizational data retention policies.</p>
      </div>
      <div class="feature-card">
        <h4>5. Runtime & Kernel Controls</h4>
        <p>View running kernel sessions across all containers and force-restart hung kernels to reclaim server RAM.</p>
      </div>
      <div class="feature-card">
        <h4>6. Security Audit Logs</h4>
        <p>Immutable event log recording all logins, privilege escalations, package installations, and system configuration changes.</p>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 23: AI Coding Assistant -->
<!-- ========================================================================= -->
<section id="ch23" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 23</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">AI Coding Assistant</h2>
    <p class="section-lead">
      Harness the built-in AI assistant to generate Python code, explain tricky tracebacks, and insert working code directly into your notebook.
    </p>
  </div>

  <div class="content-block">
    <h3>Accessing the AI Assistant</h3>
    <ol>
      <li>Click the <strong>AI Assistant</strong> tab located in the Right Collapsible Panel.</li>
      <li>Type your question or coding request into the chat box (e.g., <em>"How do I filter rows with missing values in Pandas?"</em>).</li>
      <li>The AI streams an explanation alongside a tested code snippet.</li>
      <li>Click <strong>Insert in Notebook</strong> to automatically append the code into a new cell on your active notebook canvas!</li>
    </ol>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 24: Keyboard Shortcuts Matrix -->
<!-- ========================================================================= -->
<section id="ch24" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 24</span>
      <span class="section-reading-time">3 min reference</span>
    </div>
    <h2 class="section-title">Keyboard Shortcuts Matrix</h2>
    <p class="section-lead">
      Comprehensive reference of all productivity keyboard shortcuts for Windows, Linux, and macOS.
    </p>
  </div>

  <div class="content-block">
    <table class="comparison-table">
      <thead>
        <tr>
          <th>Action</th>
          <th>Windows / Linux</th>
          <th>macOS</th>
          <th>Context</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Run Cell (Stay)</strong></td>
          <td><kbd>Ctrl</kbd> + <kbd>Enter</kbd></td>
          <td><kbd>⌘</kbd> + <kbd>Enter</kbd></td>
          <td>Active Code Cell</td>
        </tr>
        <tr>
          <td><strong>Run Cell & Advance</strong></td>
          <td><kbd>Shift</kbd> + <kbd>Enter</kbd></td>
          <td><kbd>Shift</kbd> + <kbd>Enter</kbd></td>
          <td>Active Code Cell</td>
        </tr>
        <tr>
          <td><strong>Run & Insert Cell Below</strong></td>
          <td><kbd>Alt</kbd> + <kbd>Enter</kbd></td>
          <td><kbd>Option</kbd> + <kbd>Enter</kbd></td>
          <td>Active Code Cell</td>
        </tr>
        <tr>
          <td><strong>Save Notebook</strong></td>
          <td><kbd>Ctrl</kbd> + <kbd>S</kbd></td>
          <td><kbd>⌘</kbd> + <kbd>S</kbd></td>
          <td>Anywhere</td>
        </tr>
        <tr>
          <td><strong>Toggle Left Sidebar</strong></td>
          <td><kbd>Ctrl</kbd> + <kbd>B</kbd></td>
          <td><kbd>⌘</kbd> + <kbd>B</kbd></td>
          <td>Anywhere</td>
        </tr>
        <tr>
          <td><strong>Trigger Autocomplete</strong></td>
          <td><kbd>Ctrl</kbd> + <kbd>Space</kbd></td>
          <td><kbd>Ctrl</kbd> + <kbd>Space</kbd></td>
          <td>Editor Cursor</td>
        </tr>
        <tr>
          <td><strong>Accept Suggestion</strong></td>
          <td><kbd>Tab</kbd> or <kbd>Enter</kbd></td>
          <td><kbd>Tab</kbd> or <kbd>Enter</kbd></td>
          <td>Autocomplete Open</td>
        </tr>
        <tr>
          <td><strong>Dismiss Popup</strong></td>
          <td><kbd>Escape</kbd></td>
          <td><kbd>Escape</kbd></td>
          <td>Active Dropdown</td>
        </tr>
        <tr>
          <td><strong>Search User Guide</strong></td>
          <td><kbd>Ctrl</kbd> + <kbd>K</kbd></td>
          <td><kbd>⌘</kbd> + <kbd>K</kbd></td>
          <td>This Documentation</td>
        </tr>
      </tbody>
    </table>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 25: Troubleshooting Knowledge Base -->
<!-- ========================================================================= -->
<section id="ch25" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 25</span>
      <span class="section-reading-time">6 min read</span>
    </div>
    <h2 class="section-title">Troubleshooting Knowledge Base</h2>
    <p class="section-lead">
      Step-by-step diagnostic trees and resolution procedures for common operational issues.
    </p>
  </div>

  <div class="content-block">
    <div class="error-fix-card">
      <div class="error-badge-header">
        <span class="badge badge-error">Issue: Kernel Status Shows "Disconnected"</span>
      </div>
      <p><strong>Symptom:</strong> The status pill in the top navbar shows red Disconnected and code cells will not run.</p>
      <p><strong>Solution:</strong> Check your local network or backend server. If running locally, ensure <code>uvicorn</code> on port 8765 is active. Refresh your browser tab. Cloud Studio automatically attempts reconnection.</p>
    </div>

    <div class="error-fix-card">
      <div class="error-badge-header">
        <span class="badge badge-error">Issue: ModuleNotFoundError Immediately After Installing</span>
      </div>
      <p><strong>Symptom:</strong> You ran <code>pip install package</code> in a terminal or cell, but Python says module not found.</p>
      <p><strong>Solution:</strong> Always use <code>%pip install &lt;package&gt;</code> (with the percent <code>%</code> prefix) inside a code cell. This guarantees the package is installed into the exact Python interpreter running the notebook kernel.</p>
    </div>

    <div class="error-fix-card">
      <div class="error-badge-header">
        <span class="badge badge-error">Issue: Code Stuck in Busy State (Infinite Loop)</span>
      </div>
      <p><strong>Symptom:</strong> The run button continuously spins and the status remains <code>Python 3 (busy)</code>.</p>
      <p><strong>Solution:</strong> Click the <strong>Restart Kernel</strong> button in the top navbar. This sends a SIGTERM/SIGKILL signal to the hung process and restarts a clean kernel.</p>
    </div>

    <div class="error-fix-card">
      <div class="error-badge-header">
        <span class="badge badge-error">Issue: File Not Found When Reading CSV</span>
      </div>
      <p><strong>Symptom:</strong> <code>FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'</code></p>
      <p><strong>Solution:</strong> Check the Left Files Sidebar. Confirm the exact spelling and extension of the file. If inside a subfolder, include the folder path (e.g., <code>pd.read_csv("datasets/data.csv")</code>).</p>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 26: Frequently Asked Questions (FAQ) -->
<!-- ========================================================================= -->
<section id="ch26" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 26</span>
      <span class="section-reading-time">5 min read</span>
    </div>
    <h2 class="section-title">Frequently Asked Questions (FAQ)</h2>
    <p class="section-lead">
      Answers to the most common beginner, technical, and administration questions.
    </p>
  </div>

  <div class="content-block">
    <div class="accordion-item">
      <div class="accordion-header"><h4>Q1: Do I need to install Python on my computer to use this?</h4></div>
      <div class="accordion-content">
        <p>No! Python Cloud Studio runs entirely in the cloud. All code execution happens on the remote server kernel.</p>
      </div>
    </div>

    <div class="accordion-item">
      <div class="accordion-header"><h4>Q2: Will my work be saved if I close the browser?</h4></div>
      <div class="accordion-content">
        <p>If you are signed in to a private account, your notebooks and uploaded datasets remain permanently saved in your private workspace. Remember to press <kbd>Ctrl+S</kbd> to save recent changes before closing.</p>
      </div>
    </div>

    <div class="accordion-item">
      <div class="accordion-header"><h4>Q3: Can I export my notebooks to run on Google Colab or VS Code?</h4></div>
      <div class="accordion-content">
        <p>Yes. Open the Notebooks Modal and click <strong>Download .ipynb</strong>. The downloaded file is a standard Jupyter Notebook v4 file compatible with Google Colab, VS Code, and JupyterLab.</p>
      </div>
    </div>

    <div class="accordion-item">
      <div class="accordion-header"><h4>Q4: How do I resize tall code cells?</h4></div>
      <div class="accordion-content">
        <p>Hover your cursor over the horizontal drag handle at the bottom of the code cell. Click and drag up or down to set any height between 80px and 800px. The height is saved automatically!</p>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 27: Quick Start Cheat Sheet -->
<!-- ========================================================================= -->
<section id="ch27" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 27</span>
      <span class="section-reading-time">Printable Reference</span>
    </div>
    <h2 class="section-title">Quick Start Cheat Sheet</h2>
    <p class="section-lead">
      High-density, printable quick-reference sheet for everyday Python coding in Cloud Studio.
    </p>
  </div>

  <div class="content-block">
    <div class="three-column-grid">
      <div class="feature-card">
        <h4>Python Basics</h4>
        <div class="code-container">
          <pre class="code-pre"><code># Variables & Printing
x = 10
print(f"Value: {x}")

# Lists & Loops
items = [1, 2, 3]
for item in items:
    print(item * 2)</code></pre>
        </div>
      </div>

      <div class="feature-card">
        <h4>Pandas Essentials</h4>
        <div class="code-container">
          <pre class="code-pre"><code>import pandas as pd

df = pd.read_csv("data.csv")
df.head()        # View top 5 rows
df.describe()    # Summary stats
df[df["col"] &gt; 5] # Filter rows</code></pre>
        </div>
      </div>

      <div class="feature-card">
        <h4>Matplotlib Plotting</h4>
        <div class="code-container">
          <pre class="code-pre"><code>import matplotlib.pyplot as plt

plt.figure(figsize=(8, 4))
plt.plot(x, y, label="Trend")
plt.title("Title")
plt.legend()
plt.show()</code></pre>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 28: Comprehensive Glossary -->
<!-- ========================================================================= -->
<section id="ch28" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 28</span>
      <span class="section-reading-time">4 min reference</span>
    </div>
    <h2 class="section-title">Comprehensive Glossary</h2>
    <p class="section-lead">
      Clear definitions for every core concept, architecture component, and terminology used in Python Cloud Studio.
    </p>
  </div>

  <div class="content-block">
    <dl class="glossary-list">
      <dt>Kernel</dt>
      <dd>The background Python process that receives code from the web frontend, executes statements in memory, and returns stdout/outputs.</dd>

      <dt>ZeroMQ (ZMQ)</dt>
      <dd>The high-performance asynchronous messaging library used to route commands between the web server and the IPython kernel.</dd>

      <dt>Monaco Editor</dt>
      <dd>The open-source code editor component powering Visual Studio Code and Python Cloud Studio's code cells.</dd>

      <dt>DataTableView</dt>
      <dd>Cloud Studio's interactive table component for sorting, filtering, and exporting Pandas DataFrames.</dd>

      <dt>Diagnostics</dt>
      <dd>Real-time static code analysis that flags syntax errors and missing imports with red squiggly underlines.</dd>

      <dt>Public Workspace</dt>
      <dd>The zero-login guest sandbox environment where temporary files can be created and tested without an account.</dd>

      <dt>Private Workspace</dt>
      <dd>The isolated tenant storage directory assigned to a registered user, protected by JWT authentication.</dd>
    </dl>
  </div>
</section>
"""

