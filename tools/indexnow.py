#!/usr/bin/env python3
"""Ping IndexNow (Bing, Yandex, Seznam, Naver...) with every URL in sitemap.xml. Run after each deploy,
once GitHub Pages has published the change.

The IndexNow key is public by design: it is served at https://towing.ge/<KEY>.txt
(the secret Bing Webmaster API key is NOT this — that one lives in macOS Keychain, see tools/bing_submit.py).
Usage: python3 tools/indexnow.py [url ...]   (no args: every URL in sitemap.xml)
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

KEY = "87cdb26581a12c3e4d89fec5d8bffb31"
HOST = "towing.ge"
ROOT = Path(__file__).resolve().parent.parent

urls = sys.argv[1:] or re.findall(r"<loc>\s*(.*?)\s*</loc>", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
with urllib.request.urlopen(req, timeout=30) as r:
    print(r.status, len(urls), "urls sent to IndexNow")
