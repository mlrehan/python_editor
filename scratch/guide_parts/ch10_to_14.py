"""
Chapters 10 through 14 for Python Cloud Studio User Guide.
"""

def get_chapters_10_to_14():
    return """
<!-- ========================================================================= -->
<!-- CHAPTER 10: NumPy & Pandas DataFrames (Interactive DataTableView) -->
<!-- ========================================================================= -->
<section id="ch10" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 10</span>
      <span class="section-reading-time">6 min read</span>
    </div>
    <h2 class="section-title">NumPy & Pandas DataFrames (Interactive DataTableView)</h2>
    <p class="section-lead">
      Learn how to manipulate tabular data with Pandas and leverage Python Cloud Studio's upgraded interactive table viewer.
    </p>
  </div>

  <div class="content-block">
    <h3>The Power of Pandas in Cloud Studio</h3>
    <p>
      <strong>Pandas</strong> is Python's premier data manipulation library. Whenever you display a Pandas DataFrame (for example, by typing <code>df</code> on the last line of a code cell), Python Cloud Studio automatically intercepts the HTML table output and upgrades it into a rich, interactive <strong>DataTableView</strong> component.
    </p>

    <!-- Visual Interactive Table Mockup -->
    <div class="diagram-container">
      <div class="diagram-title">DataTableView — Interactive Component Architecture</div>
      <div class="table-view-mockup">
        <!-- Control Toolbar -->
        <div class="tv-toolbar">
          <div class="tv-search-box">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            <input type="text" placeholder="Filter rows across all columns..." value="Engineering" readonly />
          </div>
          <div class="tv-actions">
            <span class="tv-pill-action">📋 Copy TSV</span>
            <span class="tv-pill-action">⬇ Download CSV</span>
            <span class="tv-page-select">Show 10 rows ▾</span>
          </div>
        </div>

        <!-- Rendered Table Grid -->
        <div class="tv-table-wrapper">
          <table class="tv-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Employee Name <span class="tv-sort-icon">▲</span></th>
                <th>Department</th>
                <th>Salary ($) <span class="tv-sort-icon">▼</span></th>
                <th>Performance</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>1</td>
                <td>Alex Rivera</td>
                <td><span class="badge badge-verified">Engineering</span></td>
                <td>$124,500</td>
                <td>Excellent</td>
              </tr>
              <tr>
                <td>2</td>
                <td>Elena Rostova</td>
                <td><span class="badge badge-verified">Engineering</span></td>
                <td>$138,200</td>
                <td>Exceptional</td>
              </tr>
              <tr>
                <td>3</td>
                <td>Marcus Vance</td>
                <td><span class="badge badge-verified">Engineering</span></td>
                <td>$115,000</td>
                <td>Good</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Table Footer -->
        <div class="tv-footer">
          <span>Showing 1 to 3 of 3 filtered entries (filtered from 50 total records)</span>
          <div class="tv-pagination">
            <button class="tv-btn" disabled>« Previous</button>
            <span class="tv-page-num active">1</span>
            <button class="tv-btn" disabled>Next »</button>
          </div>
        </div>
      </div>
    </div>

    <h3>Key Capabilities of DataTableView</h3>
    <div class="two-column-grid">
      <div class="feature-card">
        <h4>1. Instant Column Sorting</h4>
        <p>Click any column header to sort in ascending order (<code>▲</code>). Click again to sort in descending order (<code>▼</code>). Works seamlessly on text, numbers, dates, and currency.</p>
      </div>
      <div class="feature-card">
        <h4>2. Live Real-Time Filtering</h4>
        <p>Type into the filter bar to immediately isolate rows matching your search query across all columns simultaneously—no code modification needed.</p>
      </div>
      <div class="feature-card">
        <h4>3. Customizable Page Sizes</h4>
        <p>Choose from 10, 25, 50, 100, or "All" rows per page. High-density virtualization ensures smooth scrolling even on massive datasets.</p>
      </div>
      <div class="feature-card">
        <h4>4. One-Click TSV Copy & CSV Export</h4>
        <p>Click <strong>Copy TSV</strong> to paste directly into Microsoft Excel or Google Sheets. Click <strong>Download CSV</strong> to save the table to your local hard drive.</p>
      </div>
    </div>

    <h3>Example Code: Creating an Interactive DataFrame</h3>
    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>import pandas as pd
import numpy as np

# Create a sample DataFrame
data = {
    "Employee": ["Alex Rivera", "Sarah Chen", "Elena Rostova", "Marcus Vance", "Priya Patel"],
    "Department": ["Engineering", "Product", "Engineering", "Engineering", "Marketing"],
    "Salary": [124500, 132000, 138200, 115000, 98000],
    "Tenure_Years": [3.5, 4.0, 5.2, 2.1, 1.8]
}

df = pd.DataFrame(data)
df  # Simply evaluate 'df' on the last line to activate DataTableView</code></pre>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 11: Charts & Visualizations -->
<!-- ========================================================================= -->
<section id="ch11" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 11</span>
      <span class="section-reading-time">5 min read</span>
    </div>
    <h2 class="section-title">Charts & Visualizations</h2>
    <p class="section-lead">
      Create publication-quality charts using Matplotlib and Seaborn, rendered directly inside your notebook output.
    </p>
  </div>

  <div class="content-block">
    <h3>Built-in Visualization Libraries</h3>
    <p>
      Python Cloud Studio comes with <strong>Matplotlib</strong> and <strong>Seaborn</strong> pre-configured. When you call <code>plt.show()</code>, the chart is captured as a high-density PNG graphic and embedded directly beneath your code cell.
    </p>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>import matplotlib.pyplot as plt
import numpy as np

# Generate sample trend data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

plt.figure(figsize=(9, 4), dpi=100)
plt.plot(x, y1, label="Sine Wave", color="#2563eb", linewidth=2.5)
plt.plot(x, y2, label="Cosine Wave", color="#10b981", linewidth=2.5, linestyle="--")

plt.title("Trigonometric Signal Analysis", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Time (seconds)", fontsize=11)
plt.ylabel("Signal Amplitude", fontsize=11)
plt.legend(frameon=True, loc="upper right")
plt.grid(True, linestyle=":", alpha=0.6)
plt.tight_layout()
plt.show()</code></pre>
    </div>

    <!-- Visual Chart Simulation -->
    <div class="diagram-container">
      <div class="diagram-title">Rendered Output: Inline Matplotlib Plot</div>
      <div class="chart-sim-box">
        <svg viewBox="0 0 700 220" class="chart-svg">
          <!-- Background Grid Lines -->
          <line x1="50" y1="30" x2="650" y2="30" stroke="var(--border-color)" stroke-dasharray="3,3" />
          <line x1="50" y1="80" x2="650" y2="80" stroke="var(--border-color)" stroke-dasharray="3,3" />
          <line x1="50" y1="130" x2="650" y2="130" stroke="var(--border-color)" stroke-dasharray="3,3" />
          <line x1="50" y1="180" x2="650" y2="180" stroke="var(--border-color)" stroke-dasharray="3,3" />
          <!-- Axes -->
          <line x1="50" y1="130" x2="650" y2="130" stroke="var(--text-muted)" stroke-width="1.5" />
          <!-- Sine Curve (Blue) -->
          <path d="M 50,130 Q 125,10 200,130 T 350,130 T 500,130 T 650,130" fill="none" stroke="#2563eb" stroke-width="3" />
          <!-- Cosine Curve (Green Dashed) -->
          <path d="M 50,30 Q 125,130 200,210 T 350,30 T 500,210 T 650,30" fill="none" stroke="#10b981" stroke-width="2.5" stroke-dasharray="6,4" />
          <!-- Legend Box -->
          <rect x="520" y="35" width="120" height="45" rx="4" fill="var(--bg-card)" stroke="var(--border-color)" />
          <line x1="530" y1="48" x2="555" y2="48" stroke="#2563eb" stroke-width="3" />
          <text x="562" y="52" fill="var(--text-primary)" font-size="11" font-family="sans-serif">Sine Wave</text>
          <line x1="530" y1="65" x2="555" y2="65" stroke="#10b981" stroke-width="2.5" stroke-dasharray="4,2" />
          <text x="562" y="69" fill="var(--text-primary)" font-size="11" font-family="sans-serif">Cosine Wave</text>
        </svg>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 12: Uploading & Using Datasets -->
<!-- ========================================================================= -->
<section id="ch12" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 12</span>
      <span class="section-reading-time">5 min read</span>
    </div>
    <h2 class="section-title">Uploading & Using Datasets</h2>
    <p class="section-lead">
      Step-by-step instructions for uploading CSV, Excel, and JSON files, inspecting them in the Tabbed Editor, and loading them into your code.
    </p>
  </div>

  <div class="content-block">
    <h3>Uploading Files to Your Workspace</h3>
    <p>
      Python Cloud Studio makes uploading datasets effortless. You can use either the file toolbar or direct drag-and-drop:
    </p>

    <div class="step-card">
      <div class="step-num">1</div>
      <div class="step-content">
        <h4>Click the Upload Button in the Left Sidebar</h4>
        <p>In the Left Files Sidebar, click the <strong>Upload</strong> button (or drag files from your computer folder directly into the sidebar panel). Select your dataset (e.g., <code>housing_data.csv</code>).</p>
      </div>
    </div>

    <div class="step-card">
      <div class="step-num">2</div>
      <div class="step-content">
        <h4>Verify in the Files Tree</h4>
        <p>The file appears immediately in your file tree. If you are logged in, it is securely stored in your private workspace. If you are a guest, it is stored in the public workspace.</p>
      </div>
    </div>

    <div class="step-card">
      <div class="step-num">3</div>
      <div class="step-content">
        <h4>Optional: Inspect in the Tabbed File Editor</h4>
        <p>Double-click the CSV file in the sidebar. A new tab opens in the <strong>Right Panel</strong> displaying the raw data with row numbers. You can make quick edits, save changes, or close the tab.</p>
      </div>
    </div>

    <div class="step-card">
      <div class="step-num">4</div>
      <div class="step-content">
        <h4>Load into Pandas with Relative File Paths</h4>
        <p>Because the Python kernel runs with its working directory set to your workspace root, you can read the file directly without typing complex system paths:</p>
        <div class="code-container">
          <div class="code-header">
            <span class="code-lang">Python</span>
            <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
          </div>
          <pre class="code-pre"><code>import pandas as pd

# Load the uploaded file directly
df = pd.read_csv("housing_data.csv")

# Display the first 5 records
df.head()</code></pre>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 13: Using the Python Debugger (breakpoint & pdb) -->
<!-- ========================================================================= -->
<section id="ch13" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 13</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Using the Python Debugger</h2>
    <p class="section-lead">
      Learn how to pause execution, inspect local variables, and step through complex functions using Python's built-in debugger.
    </p>
  </div>

  <div class="content-block">
    <div class="callout callout-info">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        Current Debugging Architecture & Roadmap
      </div>
      <div class="callout-body">
        In Python Cloud Studio, interactive debugging is powered by Python's standard <code>breakpoint()</code> hook and the <code>pdb</code> engine, paired with ANSI-color tracebacks. A visual DAP (Debug Adapter Protocol) gutter breakpoint tool with step-over/step-into buttons is actively on our development roadmap.
      </div>
    </div>

    <h3>How to Set Breakpoints in a Code Cell</h3>
    <p>
      To pause code execution at a specific line and inspect variables, insert <code>breakpoint()</code> where you want Python to pause:
    </p>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>def calculate_discount(price, customer_tier):
    rate = 0.05
    if customer_tier == "vip":
        rate = 0.20
    
    # Pause execution here to inspect variables
    breakpoint()
    
    final_price = price * (1 - rate)
    return final_price

result = calculate_discount(150.0, "vip")</code></pre>
    </div>

    <h3>Essential Debugger Commands</h3>
    <table class="comparison-table">
      <thead>
        <tr>
          <th>Command</th>
          <th>Name</th>
          <th>What It Does</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><kbd>p variable</kbd></td>
          <td>Print Variable</td>
          <td>Evaluates and prints the current value of <code>variable</code> (e.g., <code>p rate</code>).</td>
        </tr>
        <tr>
          <td><kbd>n</kbd></td>
          <td>Next</td>
          <td>Executes the current line and advances to the next line in the function.</td>
        </tr>
        <tr>
          <td><kbd>s</kbd></td>
          <td>Step In</td>
          <td>Steps inside the function call on the current line.</td>
        </tr>
        <tr>
          <td><kbd>c</kbd></td>
          <td>Continue</td>
          <td>Resumes normal program execution until the next breakpoint.</td>
        </tr>
        <tr>
          <td><kbd>q</kbd></td>
          <td>Quit</td>
          <td>Terminates the debugger immediately.</td>
        </tr>
      </tbody>
    </table>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 14: Python Errors & How to Fix Them -->
<!-- ========================================================================= -->
<section id="ch14" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 14</span>
      <span class="section-reading-time">6 min read</span>
    </div>
    <h2 class="section-title">Python Errors & How to Fix Them</h2>
    <p class="section-lead">
      A beginner's visual field guide to understanding common Python exceptions, identifying the root cause, and applying the permanent fix.
    </p>
  </div>

  <div class="content-block">
    <p>
      Errors are an expected part of every programmer's journey. When Python encounters an issue, Cloud Studio prints an ANSI-formatted error traceback showing the file, line number, and exact reason.
    </p>

    <!-- Error 1: SyntaxError -->
    <div class="error-fix-card">
      <div class="error-badge-header">
        <span class="badge badge-error">SyntaxError: invalid syntax</span>
        <span class="error-frequency">Most Common</span>
      </div>
      <p><strong>Cause:</strong> Python cannot understand the structure of your code—often a missing colon <code>:</code>, unclosed quotation mark, or mismatched bracket.</p>
      <div class="two-column-grid">
        <div class="code-container">
          <div class="code-header"><span class="code-lang">❌ Broken Code</span></div>
          <pre class="code-pre"><code>if age &gt;= 18  # Missing colon!
    print("Eligible")</code></pre>
        </div>
        <div class="code-container">
          <div class="code-header"><span class="code-lang">✔ Fixed Code</span></div>
          <pre class="code-pre"><code>if age &gt;= 18:  # Added colon
    print("Eligible")</code></pre>
        </div>
      </div>
    </div>

    <!-- Error 2: NameError -->
    <div class="error-fix-card">
      <div class="error-badge-header">
        <span class="badge badge-error">NameError: name '...' is not defined</span>
        <span class="error-frequency">Frequent</span>
      </div>
      <p><strong>Cause:</strong> You are trying to use a variable or function that has not been defined yet, misspelled the name, or forgot to run the cell above where it was declared.</p>
      <div class="two-column-grid">
        <div class="code-container">
          <div class="code-header"><span class="code-lang">❌ Broken Code</span></div>
          <pre class="code-pre"><code>user_name = "Jordan"
print(username)  # Misspelled underscore!</code></pre>
        </div>
        <div class="code-container">
          <div class="code-header"><span class="code-lang">✔ Fixed Code</span></div>
          <pre class="code-pre"><code>user_name = "Jordan"
print(user_name)  # Exact match</code></pre>
        </div>
      </div>
    </div>

    <!-- Error 3: TypeError -->
    <div class="error-fix-card">
      <div class="error-badge-header">
        <span class="badge badge-error">TypeError: can only concatenate str to str</span>
        <span class="error-frequency">Frequent</span>
      </div>
      <p><strong>Cause:</strong> Combining incompatible data types, such as adding a string to an integer.</p>
      <div class="two-column-grid">
        <div class="code-container">
          <div class="code-header"><span class="code-lang">❌ Broken Code</span></div>
          <pre class="code-pre"><code>age = 25
print("Your age is: " + age)</code></pre>
        </div>
        <div class="code-container">
          <div class="code-header"><span class="code-lang">✔ Fixed Code</span></div>
          <pre class="code-pre"><code>age = 25
print(f"Your age is: {age}")  # Use f-strings</code></pre>
        </div>
      </div>
    </div>

    <!-- Error 4: ModuleNotFoundError -->
    <div class="error-fix-card">
      <div class="error-badge-header">
        <span class="badge badge-error">ModuleNotFoundError: No module named '...'</span>
        <span class="error-frequency">Environment</span>
      </div>
      <p><strong>Cause:</strong> Attempting to import a package that is not yet installed in your runtime environment.</p>
      <div class="two-column-grid">
        <div class="code-container">
          <div class="code-header"><span class="code-lang">❌ Broken Code</span></div>
          <pre class="code-pre"><code>import rich
# Fails if 'rich' is not installed</code></pre>
        </div>
        <div class="code-container">
          <div class="code-header"><span class="code-lang">✔ Fixed Code</span></div>
          <pre class="code-pre"><code># Run in a cell first:
%pip install rich

import rich  # Now succeeds immediately!</code></pre>
        </div>
      </div>
    </div>
  </div>
</section>
"""

