from playwright.sync_api import sync_playwright
import json
import os
import requests

url = "https://www.upwork.com/nx/search/jobs/?q=excel&sort=recency"
memory_file = "known_jobs.json"

if os.path.exists(memory_file):
    with open(memory_file, "r") as f:
        known_jobs = json.load(f)
else:
    known_jobs = []

current_jobs = []

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 900}
    )
    page = context.new_page()

    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(7000)

    job_tiles = page.query_selector_all("article")
    for tile in job_tiles:
        link_elem = tile.query_selector("a[href*='/jobs/']")
        if not link_elem:
            continue
        href = link_elem.get_attribute("href") or ""
        clean_url = href.split("?")[0]
        if clean_url.startswith("/"):
            clean_url = f"https://www.upwork.com{clean_url}"
        
        title = link_elem.inner_text().strip()
        if clean_url and clean_url not in [j["url"] for j in current_jobs]:
            current_jobs.append({"title": title, "url": clean_url})

    browser.close()

new_jobs = [j for j in current_jobs if j["url"] not in [k["url"] for k in known_jobs]]

with open(memory_file, "w") as f:
    json.dump(current_jobs, f, indent=2)

if new_jobs:
    report = f"*** {len(new_jobs)} NEW EXCEL JOBS FOUND ***\n\n"
    for job in new_jobs[:5]:
        report += f"• {job['title']}\n{job['url']}\n\n"

    headers = {
        "Title": "Upwork Daily Excel Alerts",
        "Click": url,
        "Priority": "high"
    }
    requests.post(
        "https://ntfy.sh/katie-upwork-alerts-2026",
        data=report.encode("utf-8"),
        headers=headers
    )
    print(report)
else:
    print("No new jobs found.")
