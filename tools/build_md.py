"""Build AI-readable Markdown for towing.ge (llms.txt convention).

For every HTML page it writes a clean Markdown copy next to it (`index.html` -> `index.html.md`,
`index-en.html` -> `index-en.html.md`), adds `<link rel="alternate" type="text/markdown">` to the
HTML head, and regenerates `llms-full.txt` (all pages in one file).

Run from the repo root after editing any page:  python3 tools/build_md.py
"""
import re
import subprocess
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://towing.ge"

# Facts block prepended to every page, per language (kept short and factual for answer engines).
FACTS = {
    "ka": ("## ძირითადი ინფორმაცია\n"
           "- კომპანია: Towing.ge — ევაკუატორი თბილისი\n"
           "- ტელეფონი: +995 514 90 80 90 (WhatsApp / Viber)\n"
           "- ელ-ფოსტა: info@towing.ge\n"
           "- სამუშაო საათები: 24/7, დასვენების და სადღესასწაულო დღეების ჩათვლით\n"
           "- მისვლის დრო: თბილისში ჩვეულებრივ 20–30 წუთი\n"
           "- მომსახურების არეალი: თბილისის ყველა უბანი და მთელი საქართველო\n"
           "- მისამართი: ხიზანიშვილის ქუჩა, თბილისი 0167, საქართველო\n"
           "- Google-ზე შეფასება: https://g.page/r/CW1gUxKtUO8rECE/review\n"),
    "en": ("## Key facts\n"
           "- Business: Towing.ge — tow truck service in Tbilisi, Georgia\n"
           "- Phone: +995 514 90 80 90 (WhatsApp / Viber)\n"
           "- Email: info@towing.ge\n"
           "- Hours: 24/7, including weekends and holidays\n"
           "- Arrival time: typically 20–30 minutes within Tbilisi\n"
           "- Service area: all Tbilisi districts and all of Georgia\n"
           "- Address: Khizanishvili street, Tbilisi 0167, Georgia\n"
           "- Review us on Google: https://g.page/r/CW1gUxKtUO8rECE/review\n"),
    "ru": ("## Основная информация\n"
           "- Компания: Towing.ge — эвакуатор в Тбилиси\n"
           "- Телефон: +995 514 90 80 90 (WhatsApp / Viber)\n"
           "- Email: info@towing.ge\n"
           "- Режим работы: 24/7, включая выходные и праздники\n"
           "- Время прибытия: по Тбилиси обычно 20–30 минут\n"
           "- Зона обслуживания: все районы Тбилиси и вся Грузия\n"
           "- Адрес: улица Хизанишвили, Тбилиси 0167, Грузия\n"
           "- Оцените нас в Google: https://g.page/r/CW1gUxKtUO8rECE/review\n"),
}

SKIP_TAGS = {"script", "style", "nav", "noscript", "svg", "button", "picture", "img", "footer"}
SKIP_CLASSES = {"call-button", "breadcrumb"}
SKIP_IDS = {"top-ge-counter-container"}
BLOCK = {"p", "div", "section", "header", "footer", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6",
         "details", "summary", "br", "hr", "aside", "article"}


class ToMarkdown(HTMLParser):
    def __init__(self, page_url):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.out = []
        self.skip = 0          # depth inside skipped subtree
        self.stack = []        # (tag, skipped?)
        self.href = None
        self.link_text = []
        self.list_depth = 0

    def _abs(self, href):
        if href.startswith(("http://", "https://", "mailto:", "tel:", "viber:")):
            return href
        if href.startswith("#"):
            return self.page_url + href
        base = self.page_url if self.page_url.endswith("/") else self.page_url.rsplit("/", 1)[0] + "/"
        if href.startswith("/"):
            return SITE + href
        return base + href

    def emit(self, text):
        if self.href is not None:
            self.link_text.append(text)
        else:
            self.out.append(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = set((a.get("class") or "").split())
        skipped = self.skip > 0 or tag in SKIP_TAGS or cls & SKIP_CLASSES or a.get("id") in SKIP_IDS
        if tag in ("br", "hr", "img", "source", "meta", "link", "input"):
            if not skipped and tag == "br":
                self.emit("  \n")
            return
        self.stack.append((tag, bool(skipped)))
        if skipped:
            self.skip += 1
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.emit("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "summary":
            self.emit("\n\n### ")
        elif tag in ("ul", "ol"):
            self.list_depth += 1
            self.emit("\n")
        elif tag == "li":
            self.emit("\n" + "  " * (self.list_depth - 1) + "- ")
        elif tag in ("strong", "b"):
            self.emit("**")
        elif tag == "a" and a.get("href"):
            self.href = self._abs(a["href"])
            self.link_text = []
        elif tag in BLOCK:
            self.emit("\n\n")

    def handle_endtag(self, tag):
        if tag in ("br", "hr", "img", "source", "meta", "link", "input"):
            return
        while self.stack:
            t, skipped = self.stack.pop()
            if skipped:
                self.skip -= 1
            if t == tag:
                break
        else:
            return
        if skipped:
            return
        if tag in ("strong", "b"):
            self.emit("**")
        elif tag == "a" and self.href is not None:
            text = re.sub(r"\s+", " ", "".join(self.link_text)).strip()
            href, self.href = self.href, None
            if text:
                if self.out and self.out[-1].endswith(")") and self.out[-1].startswith("["):
                    self.out.append(" · ")
                self.out.append(f"[{text}]({href})")
        elif tag in ("ul", "ol"):
            self.list_depth -= 1
            self.emit("\n")
        elif tag in BLOCK:
            self.emit("\n\n")

    def handle_data(self, data):
        if self.skip:
            return
        text = re.sub(r"\s+", " ", data)
        if text.strip():
            self.emit(text)

    def markdown(self):
        md = "".join(self.out)
        md = re.sub(r"[ \t]+\n", "\n", md)
        md = re.sub(r"\n(#+|-) +", lambda m: "\n" + m.group(1) + " ", md)
        md = re.sub(r"\n{3,}", "\n\n", md)
        md = re.sub(r"\*\*\s*\*\*", "", md)
        # numbered step badges ("- 1" + bold title) -> ordered list item
        md = re.sub(r"\n- (\d+)\s*\n\s*\*\*", r"\n\1. **", md)
        # drop empty list items / headings left by skipped icons
        md = re.sub(r"\n- *\n", "\n", md)
        md = re.sub(r"\n#+ *\n", "\n", md)
        # list items must not be separated by blank lines
        md = re.sub(r"(\n- [^\n]*)\n\n(?=- )", r"\1\n", md)
        md = re.sub(r"(\n- [^\n]*)\n\n(?=- )", r"\1\n", md)
        return md.strip() + "\n"


def page_url(rel):
    if rel.endswith("index.html"):
        return f"{SITE}/{rel[:-len('index.html')]}"
    return f"{SITE}/{rel}"


def build(rel):
    src = (ROOT / rel).read_text(encoding="utf-8")
    lang = re.search(r'<html lang="(\w+)"', src).group(1)
    title = unescape(re.search(r"<title>(.*?)</title>", src, re.S).group(1).strip())
    desc = unescape(re.search(r'<meta name="description" content="([^"]*)"', src).group(1))
    body = re.search(r"<body[^>]*>(.*)</body>", src, re.S).group(1)
    # JSON-LD lives in <head>; inline FAQ JSON-LD in body is skipped as <script>
    conv = ToMarkdown(page_url(rel))
    conv.feed(body)
    content = conv.markdown()
    # the page's H1 becomes the document title (falls back to <title>)
    h1 = re.match(r"# (.*)\n", content)
    if h1:
        heading, content = h1.group(1).strip(), content[h1.end():].lstrip()
    else:
        heading = title
    url = page_url(rel)
    alts = re.findall(r'<link rel="alternate" hreflang="(\w+(?:-\w+)?)" href="([^"]+)"', src)
    lang_line = ""
    if alts:
        lang_line = "\n" + " · ".join(f"[{h}]({u})" for h, u in alts if h != "x-default") + "\n"
    md = (f"# {heading}\n\n> {desc}\n\n"
          f"Canonical: {url}\n{lang_line}\n"
          f"{FACTS[lang]}\n{content}")
    out = ROOT / (rel + ".md")
    out.write_text(md, encoding="utf-8")

    # advertise the Markdown copy from the HTML head
    md_url = f"{SITE}/{rel}.md"
    tag = f'<link rel="alternate" type="text/markdown" href="{md_url}" />'
    if tag not in src:
        src2, n = re.subn(r'(\n(\s*)<link rel="canonical"[^>]*>)', lambda m: m.group(1) + "\n" + m.group(2) + tag, src, count=1)
        assert n == 1, rel
        (ROOT / rel).write_text(src2, encoding="utf-8")
    return rel, lang, title, md


def main():
    files = subprocess.run(["git", "ls-files", "*.html"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    files += [str(p.relative_to(ROOT)) for p in ROOT.glob("**/*.html")
              if str(p.relative_to(ROOT)) not in files and "node_modules" not in p.parts]
    order = {"ka": 0, "en": 1, "ru": 2}
    pages = sorted((build(f) for f in sorted(set(files))),
                   key=lambda x: (order[x[1]], x[0] != "index.html" and not x[0].startswith("index-"), x[0]))
    full = ["# Towing.ge — full site content (ევაკუატორი თბილისი / Tow truck Tbilisi / Эвакуатор Тбилиси)\n",
            "> Every page of https://towing.ge in Markdown, for AI assistants and answer engines. "
            "Index: https://towing.ge/llms.txt\n"]
    for rel, lang, title, md in pages:
        full.append(f"\n\n---\n\nSource: {SITE}/{rel}.md\n\n{md}")
    (ROOT / "llms-full.txt").write_text("".join(full), encoding="utf-8")
    for rel, lang, title, _ in pages:
        print(f"{lang}  {rel}.md  — {title}")


if __name__ == "__main__":
    main()
