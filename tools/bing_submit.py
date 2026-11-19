#!/usr/bin/env python3
"""Submit the most important / newest URLs of towing.ge to the Bing Webmaster API.

The API key is secret and is read from macOS Keychain (account "bagrat-sites", service "bing-webmaster-api");
it is never stored in this public repo. Bing allows a limited number of URLs per day here (the script reads
the quota); tools/indexnow.py already covers every URL, this is an extra push for the key pages.
Usage: python3 tools/bing_submit.py [url ...]   (no args: key pages first, then the most recently changed)
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://towing.ge/"
key = subprocess.run(["security", "find-generic-password", "-a", "bagrat-sites", "-s", "bing-webmaster-api", "-w"],
                     capture_output=True, text=True).stdout.strip()
if not key:
    sys.exit("no Bing API key in Keychain (account bagrat-sites, service bing-webmaster-api)")
api = "https://ssl.bing.com/webmaster/api.svc/json/{}?apikey=" + key
quota = json.loads(urllib.request.urlopen(api.format("GetUrlSubmissionQuota") + "&siteUrl=" + SITE, timeout=30).read())["d"]["DailyQuota"]

urls = sys.argv[1:]
if not urls:
    pairs = re.findall(r"<loc>\s*(.*?)\s*</loc>\s*<lastmod>\s*(.*?)\s*</lastmod>", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
    first = [SITE, SITE + "evakuatori-tbilisi/", SITE + "evakuatoris-gamodzaxeba/", SITE + "services/oboba-evakuatori/",
             SITE + "services/akumulatoris-shecvla/", SITE + "services/modzravi-vulkanizacia/", SITE + "index-en.html", SITE + "index-ru.html"]
    rest = [u for u, d in sorted(pairs, key=lambda x: x[1], reverse=True) if u not in first]
    urls = first + rest
urls = urls[:quota]
if not urls:
    sys.exit("daily quota used up")
req = urllib.request.Request(api.format("SubmitUrlbatch"), data=json.dumps({"siteUrl": SITE, "urlList": urls}).encode(),
                             headers={"Content-Type": "application/json; charset=utf-8"})
with urllib.request.urlopen(req, timeout=60) as r:
    print(r.status, len(urls), "urls submitted to Bing (quota", quota, "today)")
