"""
Chapters 6 through 9 for Python Cloud Studio User Guide.
"""

def get_chapters_6_to_9():
    return """
<!-- ========================================================================= -->
<!-- CHAPTER 6: How to Write Python Code & IntelliSense -->
<!-- ========================================================================= -->
<section id="ch6" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 6</span>
      <span class="section-reading-time">5 min read</span>
    </div>
    <h2 class="section-title">How to Write Python Code & IntelliSense</h2>
    <p class="section-lead">
      Master the code editor and its shortcuts, smart autocomplete suggestions, parameter signature hints, and real-time syntax diagnostics.
    </p>
  </div>

  <div class="content-block">
    <h3>The Code Editor</h3>
    <p>
      Every code cell is a Python-aware editor with line numbers, automatic indentation, auto-closing brackets and quotes, comment toggling, and IntelliSense. The <code>.py</code> file editor in the right panel supports the same indentation and comment shortcuts.
    </p>
    <ul>
      <li><strong>Comment / uncomment:</strong> <kbd>Ctrl</kbd> + <kbd>/</kbd> (<kbd>⌘</kbd> + <kbd>/</kbd> on macOS) adds or removes <code># </code> on the current line, or on every selected line. Comments are aligned with the block's indentation, blank lines are left alone, and your selection is kept so you can press it again to undo.</li>
      <li><strong>Indent:</strong> <kbd>Tab</kbd> inserts four spaces, or indents every selected line.</li>
      <li><strong>Outdent:</strong> <kbd>Shift</kbd> + <kbd>Tab</kbd> removes one level (up to four spaces) from the current or selected lines.</li>
      <li><strong>Auto-indent:</strong> <kbd>Enter</kbd> keeps the current indentation and adds one level after a line ending in <code>:</code> (for example after <code>def</code>, <code>if</code>, <code>for</code>).</li>
    </ul>

    <h3>1. Python IntelliSense Autocomplete</h3>
    <p>
      As you type Python code, Cloud Studio actively inspects both the Python Abstract Syntax Tree (AST) and the live runtime kernel namespace to offer context-aware suggestions:
    </p>

    <div class="callout callout-info">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        Viewport-Aware Dropdown Positioning (Google Colab Style)
      </div>
      <div class="callout-body">
        <ul>
          <li><strong>Intelligent Placement:</strong> The autocomplete suggestion dropdown appears directly below your typing cursor. If there is insufficient room at the bottom of the viewport (&lt;260px), it smoothly flips <em>above</em> the cursor.</li>
          <li><strong>Keyboard Navigation:</strong> Use <kbd>Arrow Down</kbd> and <kbd>Arrow Up</kbd> to move through candidate functions, methods, and variables. The list scrolls smoothly to ensure the highlighted item is always in view.</li>
          <li><strong>Accepting Suggestions:</strong> Press <kbd>Tab</kbd> or <kbd>Enter</kbd> to insert the exact matched token.</li>
          <li><strong>Dismissing:</strong> Press <kbd>Escape</kbd> to close the autocomplete dropdown without altering your text.</li>
        </ul>
      </div>
    </div>

    <!-- Interactive Diagram / Visual Simulation of Autocomplete -->
    <div class="diagram-container">
      <div class="diagram-title">Visual Simulation: Autocomplete Dropdown in Action</div>
      <div class="autocomplete-sim-box">
        <div class="sim-editor-line">
          <span class="syn-keyword">import</span> <span class="syn-var">pandas</span> <span class="syn-keyword">as</span> <span class="syn-var">pd</span>
        </div>
        <div class="sim-editor-line">
          <span class="syn-var">pd.read_</span><span class="sim-cursor"></span>
        </div>
        <!-- Dropdown Box -->
        <div class="sim-dropdown">
          <div class="sim-item active">
            <span class="sim-icon-func">f</span>
            <span class="sim-name"><strong>read_csv</strong></span>
            <span class="sim-desc">Read a comma-separated values (csv) file into DataFrame</span>
          </div>
          <div class="sim-item">
            <span class="sim-icon-func">f</span>
            <span class="sim-name">read_excel</span>
            <span class="sim-desc">Read an Excel file into a pandas DataFrame</span>
          </div>
          <div class="sim-item">
            <span class="sim-icon-func">f</span>
            <span class="sim-name">read_json</span>
            <span class="sim-desc">Convert a JSON string to pandas object</span>
          </div>
          <div class="sim-item">
            <span class="sim-icon-func">f</span>
            <span class="sim-name">read_parquet</span>
            <span class="sim-desc">Load a parquet object from the file path</span>
          </div>
        </div>
      </div>
    </div>

    <h3>2. Parameter Signature Help</h3>
    <p>
      When you type an opening parenthesis <code>(</code> after a function name (e.g., <code>pd.read_csv(</code> or <code>plt.plot(</code>), a dedicated <strong>Parameter Signature Help</strong> box appears.
    </p>
    <ul>
      <li>Displays parameter names, default values, and the function's documentation.</li>
      <li><strong>Always visible:</strong> The box sits on the opposite side of the line from the autocomplete dropdown, and otherwise on whichever side has more room. It is sized to fit the visible part of the notebook (below the toolbar) and repositions as you scroll.</li>
      <li><strong>Interactive:</strong> Move the mouse into the box to scroll long documentation with the wheel, touchpad or scrollbar, and select text to copy it with <kbd>Ctrl</kbd> + <kbd>C</kbd>. After clicking inside it, <kbd>↑</kbd>/<kbd>↓</kbd> and <kbd>Page Up</kbd>/<kbd>Page Down</kbd> scroll it too.</li>
      <li><strong>Close and reopen:</strong> <kbd>Escape</kbd> closes the autocomplete dropdown first, then the signature box, and returns the cursor to your code. Press <kbd>Ctrl</kbd> + <kbd>Space</kbd> inside the parentheses to bring it back.</li>
    </ul>

    <h3>3. Real-Time Code Diagnostics</h3>
    <p>
      Python Cloud Studio continually checks your code for syntax mistakes, unclosed parentheses, and unresolved imports:
    </p>
    <ul>
      <li><strong>Red Squiggly Underlines:</strong> Highlight the exact error token in your code. Hover your mouse over the red line to view a clear explanation of what needs to be fixed.</li>
      <li><strong>Typing Suppression:</strong> To avoid distracting you while actively typing, diagnostics are automatically suppressed until you pause or finish your statement.</li>
      <li><strong>Automatic Refresh:</strong> When you run a cell, restart the kernel, or install a new package via <code>%pip</code>, diagnostics automatically re-evaluate and clear immediately.</li>
    </ul>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 7: Executing Code & Execution Controls -->
<!-- ========================================================================= -->
<section id="ch7" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 7</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Executing Code & Execution Controls</h2>
    <p class="section-lead">
      Learn all the ways to run code, understand the cell execution counter, run the entire notebook at once, and cancel stuck calculations.
    </p>
  </div>

  <div class="content-block">
    <h3>The Three Execution Shortcuts</h3>
    <p>
      Mastering keyboard shortcuts is the single most effective way to accelerate your Python workflow. Python Cloud Studio provides three distinct execution actions:
    </p>

    <div class="three-column-grid">
      <div class="feature-card">
        <div class="feature-card-header">
          <kbd>Ctrl</kbd> + <kbd>Enter</kbd>
        </div>
        <h4>Run & Stay in Current Cell</h4>
        <p>Runs the active cell without moving focus. Perfect when iteratively testing adjustments to the same function or chart.</p>
        <span class="badge badge-verified">Focus Preserved</span>
      </div>

      <div class="feature-card">
        <div class="feature-card-header">
          <kbd>Shift</kbd> + <kbd>Enter</kbd>
        </div>
        <h4>Run & Advance to Next Cell</h4>
        <p>Runs the active cell and automatically advances cursor focus to the next cell. If you are on the last cell, it creates a new empty cell!</p>
        <span class="badge badge-verified">Primary Workflow</span>
      </div>

      <div class="feature-card">
        <div class="feature-card-header">
          <kbd>Alt</kbd> + <kbd>Enter</kbd>
        </div>
        <h4>Run & Insert New Cell Below</h4>
        <p>Runs the active cell and immediately inserts a brand-new blank cell directly below, moving your cursor into it.</p>
        <span class="badge badge-verified">Rapid Expansion</span>
      </div>
    </div>

    <h3>Understanding the Execution Gutter</h3>
    <p>
      On the left side of every code cell is the execution gutter. It communicates three distinct states:
    </p>
    <ul>
      <li><code>[ ]</code> <strong>Not Yet Executed:</strong> The cell has not run in the current kernel session.</li>
      <li><span class="badge badge-busy">Spinning Circle</span> <strong>Running:</strong> The code is currently executing on the cloud kernel and the cell shows <code>[*]</code>. The run button turns into a red <strong>Stop</strong> square inside the spinner: click it to stop the cell. The top navbar displays <code>Python 3 (busy)</code>. Running the same cell again while it is still running is ignored, so its output is never mixed with a second run.</li>
      <li><code>[1]</code> <strong>Executed:</strong> The number indicates the exact sequential order in which this cell was executed in the current session.</li>
    </ul>

    <h3>Using "Run All"</h3>
    <p>
      Located on the top navbar, the <strong>Run All</strong> button (<kbd>▶</kbd>) sequentially executes every code cell in your notebook from the first to the last. This is standard practice before sharing your notebook or generating final reports, ensuring all variables and results are computed in top-to-bottom order.
    </p>

    <h3>Stopping a Long-Running or Infinite Loop</h3>
    <p>
      If your code runs too long or gets stuck in an infinite loop (for example, <code>while True: pass</code>), stop it without reloading the page. Any of these does the same thing:
    </p>
    <ul>
      <li>Click <strong>Stop</strong> in the top navbar. It turns red while code is running.</li>
      <li>Click the red <strong>Stop</strong> square on the running cell's run button.</li>
      <li>Press <kbd>Ctrl</kbd> + <kbd>C</kbd> (<kbd>⌃</kbd> + <kbd>C</kbd> on macOS) while a cell is running. If text is selected, <kbd>Ctrl</kbd> + <kbd>C</kbd> copies it instead, as usual.</li>
    </ul>
    <p>
      The cell ends with a <code>KeyboardInterrupt</code> message. Your variables are kept, so you can fix the code and run it again. Cells still waiting from <strong>Run All</strong> are cancelled. Programs the cell started, such as a web server launched with <code>!uvicorn</code> or <code>subprocess</code>, are stopped too. <strong>Clear Outputs</strong> only clears what is displayed; it does not stop running code.
    </p>

    <div class="callout callout-warning">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        When Stop is not enough
      </div>
      <div class="callout-body">
        <p>
          Some code cannot be interrupted, for example code stuck inside a native library call or code that ignores interrupts. If a cell is still running about 8 seconds after you press Stop, a yellow banner offers <strong>Restart kernel</strong>. Restarting always stops the code, but it clears all variables and imports, so you will need to run your cells again. Choose <strong>Keep waiting</strong> to give it more time. You can also click <strong>Restart</strong> in the top navbar at any time.
        </p>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 8: Understanding Output -->
<!-- ========================================================================= -->
<section id="ch8" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 8</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Understanding Output</h2>
    <p class="section-lead">
      Learn how Python Cloud Studio captures, formats, and renders different types of cell output, from basic print statements to rich multimedia.
    </p>
  </div>

  <div class="content-block">
    <h3>Standard Output vs. Expression Return Values</h3>
    <p>
      In Python notebooks, there is an important difference between printing something and evaluating an expression on the last line:
    </p>

    <div class="two-column-grid">
      <div class="feature-card">
        <h4>1. Standard Output (`print()`)</h4>
        <p>Text sent to Python's <code>sys.stdout</code> stream. Rendered in a clean monospace font below the cell:</p>
        <div class="code-container">
          <pre class="code-pre"><code>print("Calculating results...")
print("Step 1 complete.")</code></pre>
        </div>
        <div class="output-preview">
          <pre class="output-body">Calculating results...
Step 1 complete.</pre>
        </div>
      </div>

      <div class="feature-card">
        <h4>2. Last-Line Expression Value</h4>
        <p>If the final line of your code cell evaluates to an object or expression, the notebook displays it automatically without needing <code>print()</code>:</p>
        <div class="code-container">
          <pre class="code-pre"><code>score = 95
score * 1.05  # Automatically rendered!</code></pre>
        </div>
        <div class="output-preview">
          <div class="output-header">Out [2]:</div>
          <pre class="output-body">99.75</pre>
        </div>
      </div>
    </div>

    <h3>Rich Output Types Supported</h3>
    <p>Python Cloud Studio automatically detects and renders rich MIME types:</p>
    <ul>
      <li><strong>Pandas DataFrames:</strong> Automatically transformed into interactive, searchable, sortable tables (see Chapter 10).</li>
      <li><strong>Matplotlib & Seaborn Charts:</strong> High-resolution PNG images rendered inline with crystal-clear vector sharpness.</li>
      <li><strong>HTML & Markdown:</strong> Rendered directly using safe DOM sanitization.</li>
      <li><strong>ANSI Error Tracebacks:</strong> Python exceptions and stack traces are color-coded in high-visibility red, amber, and cyan, making errors effortless to diagnose.</li>
    </ul>
  </div>
</section>

<!-- ========================================================================= -->
<!-- CHAPTER 9: Multi-Cell & Kernel State -->
<!-- ========================================================================= -->
<section id="ch9" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-verified">Chapter 9</span>
      <span class="section-reading-time">4 min read</span>
    </div>
    <h2 class="section-title">Multi-Cell & Kernel State</h2>
    <p class="section-lead">
      Understand how memory persists across different cells, the golden rules of notebook execution order, and how to avoid hidden state bugs.
    </p>
  </div>

  <div class="content-block">
    <h3>The Shared Global Namespace</h3>
    <p>
      In a Python Cloud Studio notebook, all code cells share a <strong>single running Python kernel process</strong>.
      When you define a variable, import a library, or declare a function in one cell, it remains stored in the kernel's memory and is immediately accessible to all other cells.
    </p>

    <!-- Visual Diagram of Shared Memory -->
    <div class="diagram-container">
      <div class="diagram-title">How Notebook Cells Share Kernel Memory</div>
      <div class="state-diagram-wrapper">
        <div class="cell-node">
          <div class="node-title">Cell 1 [Executed]</div>
          <div class="node-code"><code>total_revenue = 450000</code></div>
        </div>
        <div class="node-arrow">── stores into ──▶</div>
        <div class="kernel-node">
          <div class="kernel-title">Active IPyKernel Memory</div>
          <div class="kernel-vars">
            <code>total_revenue: 450000</code><br>
            <code>tax_rate: 0.15</code>
          </div>
        </div>
        <div class="node-arrow">◀── reads from ──</div>
        <div class="cell-node">
          <div class="node-title">Cell 2 [Executed]</div>
          <div class="node-code"><code>net = total_revenue * (1 - tax_rate)</code></div>
        </div>
      </div>
    </div>

    <h3>The Out-of-Order Execution Pitfall</h3>
    <p>
      Because you can run cells in any order you choose, you might run Cell 3 before Cell 2. While flexible, this can lead to confusing bugs where code works on your screen but fails when someone else runs the notebook from top to bottom.
    </p>

    <div class="callout callout-warning">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        Best Practice: The "Restart & Run All" Test
      </div>
      <div class="callout-body">
        <p>Before saving your final work or turning in an assignment, always do this quick two-step check:</p>
        <ol>
          <li>Click the <strong>Restart</strong> button in the top navbar to clear all kernel variables.</li>
          <li>Click <strong>Run All</strong> to verify that every cell executes cleanly from top to bottom with zero errors.</li>
        </ol>
        <p>If all cells pass, your notebook is 100% reproducible and ready for production or grading!</p>
      </div>
    </div>
  </div>
</section>
"""

