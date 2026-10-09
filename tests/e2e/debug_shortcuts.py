import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright


async def main():
    server_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "services.api.main:app", "--host", "127.0.0.1", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(3)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1366, "height": 850})
            page = await context.new_page()

            page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))

            await page.goto("http://127.0.0.1:8765/", wait_until="networkidle")

            # Evaluate active cell in window
            status = await page.evaluate("""() => {
                const textareas = document.querySelectorAll('textarea');
                return {
                    count: textareas.length,
                    activeElement: document.activeElement ? document.activeElement.tagName : 'none'
                };
            }""")
            print("Initial status:", status)

            # Click textarea
            code_textarea = page.locator("textarea.code-font").first
            await code_textarea.click()
            await code_textarea.fill('print("Testing Ctrl+Enter execution")')

            val_before = await code_textarea.input_value()
            print("Value before press:", val_before)

            # Test pressing Control+Enter
            print("Pressing Control+Enter...")
            await code_textarea.press("Control+Enter")

            # Wait 3 seconds
            await asyncio.sleep(3)

            # Check outputs in DOM
            outputs = await page.evaluate("""() => {
                const pres = Array.from(document.querySelectorAll('pre')).map(p => p.innerText);
                const isRunning = document.querySelectorAll('.animate-spin').length;
                return { pres, isRunning };
            }""")
            print("DOM Outputs after Control+Enter:", outputs)

            # Now test clicking the Run button directly to compare
            print("Now clicking run button directly...")
            run_btn = page.locator("button[title*='Run cell']").first
            await run_btn.click()
            await asyncio.sleep(3)

            outputs2 = await page.evaluate("""() => {
                const pres = Array.from(document.querySelectorAll('pre')).map(p => p.innerText);
                return { pres };
            }""")
            print("DOM Outputs after Run button click:", outputs2)

            await page.screenshot(path="debug_shortcut.png")
            print("Screenshot saved to debug_shortcut.png")

            await browser.close()
    finally:
        server_process.terminate()
        server_process.kill()


if __name__ == "__main__":
    asyncio.run(main())

