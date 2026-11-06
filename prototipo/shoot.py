#!/usr/bin/env python3
"""One look at the page: wrap it like the publish skeleton, render a few states
in headless Chrome, report console errors, and compose one contact image."""
import sys
import threading
import functools
import http.server

from PIL import Image
from playwright.sync_api import sync_playwright

page_file, work, out_png = sys.argv[1], sys.argv[2], sys.argv[3]
content = open(page_file, encoding="utf-8").read()
SKEL = ("<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>"
        "<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}"
        "body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>"
        "</head><body>")
open(f"{work}/index.html", "w", encoding="utf-8").write(SKEL + content + "</body></html>")

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=work)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

shots = []
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome",
                          args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                "--ignore-gpu-blocklist"])
    def run(w, h, scheme, step, view, full=False, stage_only=False, tag=""):
        ctx = b.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, device_scale_factor=1)
        pg = ctx.new_page()
        pg.on("console", lambda m: errors.append(f"[{tag}] {m.type}: {m.text}") if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: errors.append(f"[{tag}] pageerror: {e}"))
        pg.goto(f"http://127.0.0.1:8765/index.html#paso-{step}", wait_until="networkidle")
        pg.wait_for_function("document.getElementById('stageMsg').hidden === true", timeout=30000)
        if view == "top":
            pg.click("#viewTop")
        pg.wait_for_timeout(2500)
        path = f"{work}/shot_{tag}.png"
        if stage_only:
            pg.locator("#stage").screenshot(path=path)
        else:
            pg.screenshot(path=path, full_page=full)
        shots.append(path)
        ctx.close()
    run(1280, 860, "light", 1, "persp", tag="desk-light-1")
    run(1280, 860, "light", 7, "persp", stage_only=True, tag="desk-light-7")
    run(1280, 860, "dark", 4, "top", stage_only=True, tag="desk-dark-4")
    run(390, 844, "dark", 5, "persp", full=True, tag="mobile-dark-5")
    b.close()
srv.shutdown()

ims = [Image.open(s).convert("RGB") for s in shots]
# scale each to height 860 for the sheet (mobile full page scaled to fit)
H = 860
scaled = []
for im in ims:
    s = H / im.height
    scaled.append(im.resize((max(1, int(im.width * s)), H)))
W = sum(i.width for i in scaled) + 20 * (len(scaled) - 1)
sheet = Image.new("RGB", (W, H), (255, 255, 255))
x = 0
for i in scaled:
    sheet.paste(i, (x, 0)); x += i.width + 20
sheet.save(out_png)
print("errors:", len(errors))
for e in errors[:30]:
    print(e)
