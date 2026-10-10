"""
Tutorials A through J for Python Cloud Studio User Guide.
"""

def get_tutorials():
    return """
<!-- ========================================================================= -->
<!-- TUTORIAL A: Hello World -->
<!-- ========================================================================= -->
<section id="tut-a" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial A</span>
      <span class="section-reading-time">3 min practice</span>
    </div>
    <h2 class="section-title">Tutorial A: Hello World & Modern String Formatting</h2>
    <p class="section-lead">
      Learn the universal first step in programming: creating variables, formatting strings using Python f-strings, and printing output.
    </p>
  </div>

  <div class="content-block">
    <p><strong>Goal:</strong> Write a program that greets the user with their name and displays the current year using Python.</p>
    
    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>import datetime

user_name = "Alex"
current_year = datetime.datetime.now().year

# Use Python 3.6+ f-strings for clean formatting
greeting = f"Hello, {user_name}! Welcome to Python Cloud Studio in {current_year}."
print(greeting)</code></pre>
    </div>

    <div class="output-preview">
      <div class="output-header">Output [1]:</div>
      <pre class="output-body">Hello, Alex! Welcome to Python Cloud Studio in 2026.</pre>
    </div>

    <div class="callout callout-tip">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>
        Pro Tip: Why f-strings?
      </div>
      <div class="callout-body">
        Always prefer <code>f"..."</code> strings over old-style string concatenation (<code>"Hello " + name</code>). They prevent <code>TypeError</code> when embedding numbers and make your code much easier to read.
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL B: Simple Calculator -->
<!-- ========================================================================= -->
<section id="tut-b" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial B</span>
      <span class="section-reading-time">4 min practice</span>
    </div>
    <h2 class="section-title">Tutorial B: Simple Calculator & Numerical Types</h2>
    <p class="section-lead">
      Explore integers, floats, arithmetic operators, and how Python handles mathematical calculations.
    </p>
  </div>

  <div class="content-block">
    <p><strong>Goal:</strong> Calculate the monthly payment and total cost of an equipment purchase with tax and interest.</p>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code># Define base parameters
item_price = 1200.00
sales_tax_rate = 0.0825  # 8.25%
months = 12

# Calculate totals
total_tax = item_price * sales_tax_rate
total_price = item_price + total_tax
monthly_installment = total_price / months

print(f"Base Price:       ${item_price:,.2f}")
print(f"Sales Tax:        ${total_tax:,.2f}")
print(f"Total Purchase:   ${total_price:,.2f}")
print(f"Monthly Payment:  ${monthly_installment:,.2f} / month")</code></pre>
    </div>

    <div class="output-preview">
      <div class="output-header">Output [2]:</div>
      <pre class="output-body">Base Price:       $1,200.00
Sales Tax:        $99.00
Total Purchase:   $1,299.00
Monthly Payment:  $108.25 / month</pre>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL C: Working with Lists, Dictionaries, and Loops -->
<!-- ========================================================================= -->
<section id="tut-c" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial C</span>
      <span class="section-reading-time">5 min practice</span>
    </div>
    <h2 class="section-title">Tutorial C: Lists, Dictionaries, and Loops</h2>
    <p class="section-lead">
      Organize collections of real-world information using Python lists and dictionaries, and iterate through them with loops.
    </p>
  </div>

  <div class="content-block">
    <p><strong>Goal:</strong> Manage student grade records and compute passing status.</p>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code># List of dictionaries representing students
students = [
    {"name": "Liam", "score": 88, "major": "Computer Science"},
    {"name": "Emma", "score": 94, "major": "Data Science"},
    {"name": "Noah", "score": 67, "major": "Engineering"},
    {"name": "Olivia", "score": 91, "major": "Mathematics"}
]

print("--- Course Grade Audit ---")
for student in students:
    passed = student["score"] &gt;= 70
    status = "PASS" if passed else "RETAKE"
    print(f"Student: {student['name']:<8} | Score: {student['score']} | Status: {status}")</code></pre>
    </div>

    <div class="output-preview">
      <div class="output-header">Output [3]:</div>
      <pre class="output-body">--- Course Grade Audit ---
Student: Liam     | Score: 88 | Status: PASS
Student: Emma     | Score: 94 | Status: PASS
Student: Noah     | Score: 67 | Status: RETAKE
Student: Olivia   | Score: 91 | Status: PASS</pre>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL D: Interactive Pandas Table Exploration -->
<!-- ========================================================================= -->
<section id="tut-d" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial D</span>
      <span class="section-reading-time">5 min practice</span>
    </div>
    <h2 class="section-title">Tutorial D: Interactive Pandas Table Exploration</h2>
    <p class="section-lead">
      Build a Pandas DataFrame and test the sorting, searching, and exporting powers of the interactive DataTableView component.
    </p>
  </div>

  <div class="content-block">
    <p><strong>Goal:</strong> Create a multi-column dataset and use DataTableView's interactive tools.</p>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>import pandas as pd

# Create a sample sales dataset
data = {
    "Region": ["North", "South", "East", "West", "North", "South", "East", "West"],
    "Product": ["Laptops", "Desktops", "Tablets", "Phones", "Monitors", "Laptops", "Phones", "Tablets"],
    "Units_Sold": [140, 85, 210, 340, 115, 195, 290, 180],
    "Revenue": [168000, 68000, 105000, 272000, 46000, 234000, 232000, 90000]
}

df_sales = pd.DataFrame(data)

# Evaluating df_sales activates the interactive DataTableView automatically!
df_sales</code></pre>
    </div>

    <div class="callout callout-tip">
      <div class="callout-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>
        Try These Interactive Features!
      </div>
      <div class="callout-body">
        <ul>
          <li>Click the <strong>Revenue</strong> column header to sort highest to lowest.</li>
          <li>Type <code>North</code> into the search box to filter instantly.</li>
          <li>Click <strong>Copy TSV</strong> and paste directly into Excel or Google Sheets.</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL E: CSV Upload & Summary Statistics -->
<!-- ========================================================================= -->
<section id="tut-e" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial E</span>
      <span class="section-reading-time">5 min practice</span>
    </div>
    <h2 class="section-title">Tutorial E: CSV Upload & Summary Statistics</h2>
    <p class="section-lead">
      Upload a comma-separated values (CSV) file, inspect missing values, and calculate statistical summaries.
    </p>
  </div>

  <div class="content-block">
    <p><strong>Goal:</strong> Load a local file and run an automated statistical profile.</p>

    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>import pandas as pd

# Load dataset (upload 'customers.csv' via left sidebar first)
# For this tutorial, we will generate synthetic data:
data = {
    "Age": [22, 35, 58, 41, 29, 63, 38, 47],
    "Annual_Spend": [1200, 4500, 8900, 5200, 3100, 11200, 6400, 7100],
    "Loyalty_Years": [1.0, 3.5, 7.0, 4.0, 2.0, 10.0, 4.5, 5.0]
}
df = pd.DataFrame(data)

# Generate 5-number statistical summary
df.describe()</code></pre>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL F: Matplotlib Chart Creation -->
<!-- ========================================================================= -->
<section id="tut-f" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial F</span>
      <span class="section-reading-time">5 min practice</span>
    </div>
    <h2 class="section-title">Tutorial F: Matplotlib Chart Creation</h2>
    <p class="section-lead">
      Generate an attractive comparative bar chart showing quarterly business revenue.
    </p>
  </div>

  <div class="content-block">
    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>import matplotlib.pyplot as plt

quarters = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026"]
revenue_millions = [3.2, 4.1, 4.8, 6.2, 6.9]
colors = ["#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"]

plt.figure(figsize=(8, 4.5), dpi=100)
bars = plt.bar(quarters, revenue_millions, color=colors, width=0.55)

plt.title("Quarterly Revenue Growth (USD Millions)", fontsize=13, fontweight="bold", pad=12)
plt.ylabel("Revenue ($M)", fontsize=11)
plt.ylim(0, 8)
plt.grid(axis="y", linestyle="--", alpha=0.5)

# Add values above each bar
for bar in bars:
    height = bar.get_height()
    plt.annotate(f"${height:.1f}M",
                 xy=(bar.get_x() + bar.get_width() / 2, height),
                 xytext=(0, 4), textcoords="offset points",
                 ha="center", va="bottom", fontweight="bold")

plt.tight_layout()
plt.show()</code></pre>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL G: Find & Fix Syntax Error -->
<!-- ========================================================================= -->
<section id="tut-g" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial G</span>
      <span class="section-reading-time">4 min practice</span>
    </div>
    <h2 class="section-title">Tutorial G: Find & Fix Syntax Error</h2>
    <p class="section-lead">
      Experience Cloud Studio's real-time squiggly line diagnostics and learn how to resolve syntax mistakes.
    </p>
  </div>

  <div class="content-block">
    <p><strong>Scenario:</strong> You type code with an unclosed bracket. Notice the red squiggly line appears in the editor.</p>

    <div class="code-container">
      <div class="code-header"><span class="code-lang">Python (Corrected)</span></div>
      <pre class="code-pre"><code># Notice how brackets must always balance in pairs () [] {}
temperatures = [72, 68, 75, 79, 81]  # All brackets closed

avg_temp = sum(temperatures) / len(temperatures)
print(f"Average temperature: {avg_temp:.1f}°F")</code></pre>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL H: Debugging a Function -->
<!-- ========================================================================= -->
<section id="tut-h" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial H</span>
      <span class="section-reading-time">5 min practice</span>
    </div>
    <h2 class="section-title">Tutorial H: Debugging a Function with breakpoint()</h2>
    <p class="section-lead">
      Step into a running function, inspect its local parameters, and confirm variable values before they cause bugs.
    </p>
  </div>

  <div class="content-block">
    <div class="code-container">
      <div class="code-header">
        <span class="code-lang">Python</span>
        <button class="code-copy-btn" onclick="copySnippet(this)">Copy</button>
      </div>
      <pre class="code-pre"><code>def calculate_bonus(salary, performance_score):
    multiplier = 0.05
    if performance_score &gt; 90:
        multiplier = 0.15
    elif performance_score &gt; 80:
        multiplier = 0.10
        
    bonus = salary * multiplier
    return bonus

# Test with employee record
bonus_payout = calculate_bonus(95000, 92)
print(f"Calculated Bonus: ${bonus_payout:,.2f}")</code></pre>
    </div>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL I: Save & Download Your Work -->
<!-- ========================================================================= -->
<section id="tut-i" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial I</span>
      <span class="section-reading-time">3 min practice</span>
    </div>
    <h2 class="section-title">Tutorial I: Save & Download Your Work</h2>
    <p class="section-lead">
      Protect your progress with keyboard shortcuts and export your notebook to your local computer.
    </p>
  </div>

  <div class="content-block">
    <ol>
      <li>Press <kbd>Ctrl</kbd> + <kbd>S</kbd> to save all recent cell additions and outputs.</li>
      <li>Click the <strong>Notebooks</strong> button in the top navbar.</li>
      <li>Find your current notebook card and click <strong>Download .ipynb</strong>.</li>
      <li>The file is saved to your computer, ready to submit to an instructor or open in VS Code.</li>
    </ol>
  </div>
</section>

<!-- ========================================================================= -->
<!-- TUTORIAL J: Multi-Cell Data Pipeline -->
<!-- ========================================================================= -->
<section id="tut-j" class="docs-section">
  <div class="section-header">
    <div class="section-meta">
      <span class="badge badge-tutorial">Tutorial J</span>
      <span class="section-reading-time">6 min practice</span>
    </div>
    <h2 class="section-title">Tutorial J: End-to-End Multi-Cell Data Pipeline</h2>
    <p class="section-lead">
      Connect three code cells together: Cell 1 ingests data, Cell 2 cleans and computes KPIs, and Cell 3 charts the results.
    </p>
  </div>

  <div class="content-block">
    <h4>Cell 1: Ingest Raw Data</h4>
    <div class="code-container">
      <pre class="code-pre"><code>import pandas as pd
import matplotlib.pyplot as plt

raw_data = {
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    "Signups": [1200, 1450, 1900, 2300, 2800, 3400],
    "Churn": [45, 52, 60, 71, 80, 89]
}
df_metrics = pd.DataFrame(raw_data)
print("✔ Cell 1 Complete: Raw metrics ingested.")</code></pre>
    </div>

    <h4>Cell 2: Compute Net Growth</h4>
    <div class="code-container">
      <pre class="code-pre"><code># Notice df_metrics is shared across cells!
df_metrics["Net_Gain"] = df_metrics["Signups"] - df_metrics["Churn"]
df_metrics["Growth_Pct"] = df_metrics["Net_Gain"].pct_change() * 100
df_metrics</code></pre>
    </div>

    <h4>Cell 3: Visualize Growth Trend</h4>
    <div class="code-container">
      <pre class="code-pre"><code>plt.figure(figsize=(7.5, 3.8))
plt.plot(df_metrics["Month"], df_metrics["Net_Gain"], marker="o", color="#2563eb", linewidth=2.5)
plt.title("Net Monthly User Acquisition", fontweight="bold")
plt.ylabel("Net New Users")
plt.grid(True, linestyle=":", alpha=0.6)
plt.tight_layout()
plt.show()</code></pre>
    </div>
  </div>
</section>
"""

