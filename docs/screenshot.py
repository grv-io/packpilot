import sys, time
from playwright.sync_api import sync_playwright
url, out = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1000, "height": 760}, color_scheme="light")
    pg.goto(url, wait_until="networkidle")
    pg.wait_for_selector('[data-testid="stDataFrame"]', timeout=60000)
    time.sleep(2)
    pg.add_style_tag(content="header, [data-testid='stToolbar'], [data-testid='stDecoration'], [data-testid='stStatusWidget'] {display:none !important} .block-container{padding-top:0.6rem !important; padding-left:1.2rem !important; padding-right:1.2rem !important; max-width:100% !important} h1{font-size:1.5rem !important} h3{font-size:1.15rem !important} [data-testid='stMetricValue']{font-size:1.9rem !important}")
    time.sleep(1.5)
    pg.screenshot(path=out, clip={"x": 0, "y": 0, "width": 1000, "height": 700})
    b.close()
print("saved", out)
