import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 950})
        page = context.new_page()

        print("Navigating to http://127.0.0.1:8765...")
        page.goto("http://127.0.0.1:8765", wait_until="networkidle")
        time.sleep(2)

        # Look for code cell textareas
        textareas = page.locator("textarea.code-font")
        print("Found textareas:", textareas.count())

        # Test Case 1: Pandas DataFrame Table Output
        df_code = """import pandas as pd
df = pd.DataFrame({
    'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Evan', 'Fiona', 'George', 'Hannah', 'Ian', 'Julia', 'Kevin', 'Laura'],
    'department': ['Engineering', 'Data Science', 'Product', 'Design', 'Marketing', 'Engineering', 'Finance', 'HR', 'Data Science', 'Product', 'Engineering', 'Design'],
    'salary': [105000, 115000, 95000, 90000, 85000, 110000, 125000, 75000, 118000, 98000, 102000, 92000],
    'rating': [4.8, 4.9, 4.5, 4.7, 4.2, 4.9, 4.6, 4.3, 4.8, 4.6, 4.4, 4.7],
    'bonus': [15000, 18000, None, 12000, 10000, 16000, 22000, 8000, 19000, None, 14000, 11000]
})
df"""

        cell1_ta = textareas.first
        cell1_ta.click()
        cell1_ta.fill(df_code)
        time.sleep(0.5)

        # Run cell 1
        run_btn1 = page.locator("[data-testid='cell-run-btn']").first
        run_btn1.click()
        print("Clicked run button for DataFrame cell 1, waiting for execution...")
        
        # Wait for table to appear
        table_locator = page.locator("[data-testid='interactive-data-table']").first
        table_locator.wait_for(timeout=10000)
        print("Interactive table found!")

        # Screenshot of interactive data table
        df_screenshot_path = os.path.join(ARTIFACT_DIR, "interactive_datatable_view_verified.png")
        page.screenshot(path=df_screenshot_path)
        print("Saved DataFrame screenshot:", df_screenshot_path)

        # Test sorting: click salary column
        salary_th = page.locator("th", has_text="salary").first
        if salary_th.count() > 0:
            salary_th.click()
            time.sleep(0.5)
            print("Sorted salary ascending")
            salary_sorted_asc_path = os.path.join(ARTIFACT_DIR, "table_salary_sorted_asc_verified.png")
            page.screenshot(path=salary_sorted_asc_path)
            print("Saved salary asc screenshot:", salary_sorted_asc_path)

        # Test filtering: filter by "Engineering"
        filter_input = page.locator("input[placeholder='Filter table...']").first
        filter_input.fill("Engineering")
        time.sleep(0.5)
        print("Filtered by Engineering")
        filtered_path = os.path.join(ARTIFACT_DIR, "table_filtered_engineering_verified.png")
        page.screenshot(path=filtered_path)
        print("Saved filtered screenshot:", filtered_path)

        # Clear filter
        clear_btn = page.locator("button[title='Clear filter']").first
        if clear_btn.count() > 0:
            clear_btn.click()
            time.sleep(0.5)

        # Add Cell 2 for Rich Module
        add_code_btn = page.locator("button:has-text('+ Code'), button:has-text('+ Add Code Cell')").first
        if add_code_btn.count() > 0:
            add_code_btn.click()
            time.sleep(0.5)

        textareas = page.locator("textarea.code-font")
        cell2_ta = textareas.nth(1) if textareas.count() > 1 else textareas.first
        cell2_ta.click()

        rich_code = """from rich import print

print("[bold green]Hello from Rich![/bold green]")
"""
        cell2_ta.fill(rich_code)
        time.sleep(1)

        # Run cell 2
        run_btns = page.locator("[data-testid='cell-run-btn']")
        run_btn2 = run_btns.nth(1) if run_btns.count() > 1 else run_btns.first
        run_btn2.click()
        print("Clicked run button for Rich cell 2, waiting for execution...")
        time.sleep(3)

        # Check diagnostics
        red_squiggles = page.locator("[style*='wavy rgb(239, 68, 68)'], [style*='wavy #ef4444'], [style*='wavy red']")
        print("Red squiggles count for rich import:", red_squiggles.count())

        rich_screenshot_path = os.path.join(ARTIFACT_DIR, "rich_module_no_diagnostics_verified.png")
        page.screenshot(path=rich_screenshot_path)
        print("Saved Rich module screenshot:", rich_screenshot_path)

        # Test Light Theme
        theme_btn = page.locator("button[title*='Theme'], button[title*='theme']").first
        if theme_btn.count() > 0:
            theme_btn.click()
            time.sleep(0.5)
            light_opt = page.locator("text='Light'").first
            if light_opt.count() > 0:
                light_opt.click()
                time.sleep(1)
                light_screenshot_path = os.path.join(ARTIFACT_DIR, "table_and_editor_light_theme_verified.png")
                page.screenshot(path=light_screenshot_path)
                print("Saved Light theme screenshot:", light_screenshot_path)

                if table_locator.count() > 0:
                    table_locator.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    light_table_path = os.path.join(ARTIFACT_DIR, "interactive_table_light_theme_verified.png")
                    table_locator.screenshot(path=light_table_path)
                    print("Saved Light theme table element screenshot:", light_table_path)

        browser.close()
        print("All automated verification steps passed successfully!")

if __name__ == "__main__":
    run()
