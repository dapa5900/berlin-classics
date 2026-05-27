from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(
        "https://zoopalast.premiumkino.de/specials/filmklassiker",
        wait_until="networkidle",
        timeout=30000,
    )
    page.wait_for_timeout(3000)
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "lxml")
text = soup.get_text()
lines = [l.strip() for l in text.split("\n") if l.strip() and "Minuten" in l]
print("Lines with minutes:")
for line in lines[:10]:
    print(repr(line))
