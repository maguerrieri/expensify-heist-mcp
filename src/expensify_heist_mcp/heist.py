"""The Heist: grab Expensify CSV via Safari JS injection before bot detection catches us."""

import subprocess
import time
from pathlib import Path


def run_applescript(script: str) -> str:
    """Run an AppleScript and return the output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr}")
    return result.stdout.strip()


def run_javascript(js: str) -> str:
    """Run JavaScript in the current Safari tab and return the result."""
    # Escape for AppleScript
    js_escaped = js.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
    tell application "Safari"
        do JavaScript "{js_escaped}" in current tab of window 1
    end tell
    '''
    return run_applescript(script)


def get_safari_url() -> str:
    """Get the URL of the current Safari tab."""
    script = '''
    tell application "Safari"
        get URL of current tab of window 1
    end tell
    '''
    return run_applescript(script)


def ensure_safari_window() -> None:
    """Ensure Safari has at least one window open."""
    script = '''
    tell application "Safari"
        activate
        if (count of windows) = 0 then
            make new document
        end if
    end tell
    '''
    run_applescript(script)


def set_safari_url(url: str) -> None:
    """Navigate Safari to a URL."""
    ensure_safari_window()
    script = f'''
    tell application "Safari"
        activate
        set URL of current tab of window 1 to "{url}"
    end tell
    '''
    run_applescript(script)


def close_safari_tab() -> None:
    """Close the current Safari tab."""
    script = '''
    tell application "Safari"
        close current tab of window 1
    end tell
    '''
    try:
        run_applescript(script)
    except:
        pass  # Ignore errors if tab already closed


def is_logged_in() -> bool:
    """Check if we're logged into Expensify by checking Safari URL."""
    try:
        run_applescript('tell application "Safari" to activate')
        set_safari_url("https://www.expensify.com/reports")
        time.sleep(3)  # Wait for redirect
        url = get_safari_url()
        return "/reports" in url and "sign-in" not in url.lower()
    except:
        return False


def sync_login_interactive(profile: str = "Work", timeout_seconds: int = 120) -> bool:
    """
    Open Safari for login verification.
    
    Returns True if already logged in, otherwise opens signin page.
    """
    run_applescript('tell application "Safari" to activate')
    
    # Check if already logged in
    if is_logged_in():
        return True
    
    # Navigate to sign-in
    set_safari_url("https://www.expensify.com/signin")
    
    # Poll for login completion
    print("Please log in to Expensify in Safari.")
    start = time.time()
    while time.time() - start < timeout_seconds:
        time.sleep(3)
        try:
            url = get_safari_url()
            if "sign-in" not in url.lower() and "signin" not in url.lower():
                if is_logged_in():
                    print("Login successful!")
                    return True
        except:
            pass
    
    print("Login timed out.")
    return False


def find_latest_expensify_csv(max_age_seconds: int = 300) -> Path | None:
    """Find the most recent Expensify CSV in Downloads."""
    downloads_dir = Path.home() / "Downloads"
    now = time.time()
    
    csv_files = sorted(
        downloads_dir.glob("*.csv"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    
    for csv_file in csv_files[:10]:
        # Check if file is recent enough
        if now - csv_file.stat().st_mtime > max_age_seconds:
            continue
        
        # Check if it looks like an Expensify export
        try:
            content = csv_file.read_text()
            if "Merchant" in content or "Amount" in content or "Expensify" in csv_file.name:
                return csv_file
        except:
            continue
    
    return None


def sync_fetch_expenses_csv(report_id: str | None = None, headless: bool = True, timeout: int = 60) -> tuple[str, str]:
    """
    Open Expensify reports page and automatically export via JavaScript.
    
    Closes the tab immediately after download to avoid bot detection.
    """
    run_applescript('tell application "Safari" to activate')
    
    # Navigate to reports
    set_safari_url("https://www.expensify.com/reports")
    
    # Wait for page to fully load by polling for report checkboxes
    for i in range(20):  # Wait up to 20 seconds
        time.sleep(1)
        try:
            result = run_javascript('document.querySelectorAll("input[type=checkbox]").length')
            count = int(float(result))
            if count > 10:  # Reports loaded (more than just filter checkboxes)
                break
        except:
            pass
    else:
        raise RuntimeError("Page did not load within 20 seconds")
    
    # Check if logged in
    url = get_safari_url()
    if "sign-in" in url.lower() or "signin" in url.lower():
        raise RuntimeError("Not logged in to Expensify. Please run 'expensify_login' first.")
    
    # Note the current time to find new downloads
    start_time = time.time()
    
    # Click the first report checkbox using JavaScript
    js_click_checkbox = '''
        (function() {
            var checkbox = document.querySelector('input.reportstable_checkbox');
            if (checkbox) {
                checkbox.click();
                return 'clicked';
            }
            return 'not found';
        })()
    '''
    result = run_javascript(js_click_checkbox)
    if result != "clicked":
        raise RuntimeError("No report checkboxes found on the page")
    
    time.sleep(0.5)
    
    # Click the "Export to" dropdown
    js_click_export = '''
        (function() {
            var btn = document.getElementById('button_exportButton');
            if (btn) {
                btn.click();
                return 'clicked';
            }
            return 'not found';
        })()
    '''
    result = run_javascript(js_click_export)
    if result != "clicked":
        raise RuntimeError("Export button not found")
    
    time.sleep(0.5)
    
    # Click "Default CSV" option
    js_click_csv = '''
        (function() {
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {
                if (links[i].textContent.trim() === 'Default CSV') {
                    links[i].click();
                    return 'clicked';
                }
            }
            return 'not found';
        })()
    '''
    result = run_javascript(js_click_csv)
    if result != "clicked":
        raise RuntimeError("Default CSV option not found in dropdown")
    
    # Wait for download to appear
    end_time = start_time + timeout
    while time.time() < end_time:
        csv_file = find_latest_expensify_csv(max_age_seconds=int(time.time() - start_time + 5))
        if csv_file and csv_file.stat().st_mtime > start_time:
            content = csv_file.read_text()
            # Close the tab immediately to avoid bot detection
            close_safari_tab()
            return content, csv_file.stem
        time.sleep(0.5)
    
    close_safari_tab()
    raise RuntimeError("No CSV export found. Please try again.")


def sync_list_reports(headless: bool = True) -> list[dict]:
    """List available reports. Not implemented for hybrid mode."""
    return []
