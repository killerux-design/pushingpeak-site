#!/usr/bin/env python3
"""
check-design.py — generated-design gate for pushingpeak.app.

Sibling to check-copy.py. That one asks whether the words are safe to publish;
this one asks whether the page looks like every other page an LLM has produced
this year. Both exist because this repo sits outside the app's CI and nothing
else looks at the site before it goes live.

WHY THIS EXISTS
Kevin flagged it 2026-09-02 after seeing a widely shared list of tells and,
fairly, pointing at a purple accent word I had put in a heading two minutes
after writing down that accent words in headings are a tell. A rule I have to
remember is a rule I will break. This file remembers instead.

The patterns below are drawn from what designers actually complain about, not
from taste:
  - developersdigest.tech "AI Design Slop: 16 Patterns That Out Your App as
    Vibe-Coded"
  - 925studios.co "AI Slop Web Design" (2026)
  - thefountaininstitute.com "7 Signs a UI Has Been Vibe Coded"
  - the millee.md "20 reasons why your app looks vibecoded" list Kevin sent

TWO SEVERITIES, on purpose.

  FAIL   Things with no defensible use on this site. Exit code 1.
  REVIEW Judgment calls. A colored left border is the single most recognisable
         tell, but a rule under a heading is fine, and only a human can tell
         those apart in context. Reported, never failed.

A gate that fails on judgment calls trains everyone to pass --force, which is
how check-copy.py ended up excluding /support/ and how two `&mdash;` entities
survived a commit whose entire purpose was removing them. So: the mechanical
things fail, the arguable things get printed.

THE DASH CHECK IS HERE, NOT IN check-copy.py. That gate scans rendered words
and does not look at punctuation, which is why commit 2b97fd6 removed the
literal em dash from /support/'s <title> and left two `&mdash;` entities in its
body. Entities are unescaped before counting here so that cannot happen again.

Usage:
    python3 scripts/check-design.py [paths...]

Exit codes:  0 clean · 1 a FAIL pattern was found · 2 nothing to scan
"""

import argparse
import html
import os
import re
import sys

# --------------------------------------------------------------------------
# FAIL: no defensible use on this site.
# --------------------------------------------------------------------------
FAIL = [
    (r"background-clip:\s*text|-webkit-background-clip:\s*text",
     "gradient text. Kills scannability and is decoration, not meaning."),
    (r"backdrop-filter:\s*blur",
     "glassmorphism."),
    (r"font-family:[^;}]*\b(Inter|Space Grotesk|Instrument Serif)\b",
     "the default generated typeface set. This site has Sailec."),
    (r"linear-gradient\([^)]*\b(purple|violet|indigo|#[89ab][0-9a-f]{5})\b[^)]*\)",
     "purple gradient. The single most parodied generated-design move."),
]

# --------------------------------------------------------------------------
# REVIEW: legitimate sometimes. A human reads these.
# --------------------------------------------------------------------------
REVIEW = [
    (r"border-left:\s*[2-9]px|border-right:\s*[2-9]px",
     "thick side border. Called the single most recognisable tell of generated "
     "UI when it sits on a repeated block. Fine as a one-off pull quote rule."),
    (r"text-transform:\s*uppercase",
     "all-caps label. A tell above a heading; fine on a legal footnote."),
    (r"letter-spacing:\s*\.?[1-9]",
     "wide tracking, which usually travels with an all-caps label."),
    (r"opacity:\s*0\b(?![.\d])",
     "an element parked invisible. If a scroll observer reveals it, that is "
     "fade-in-on-scroll, and the page has nothing in its first frame."),
    (r"linear-gradient|radial-gradient",
     "a gradient. Check it is carrying meaning."),
    (r"<(h[1-4])[^>]*>[^<]*<(em|span|i|b)\b",
     "an inline accent inside a heading. Colouring or italicising one phrase "
     "of a headline is a tell. Let the whole heading carry itself."),
    (r"border-radius:\s*(?:8|10|12|16)px[\s\S]{0,400}?border-radius:\s*(?:8|10|12|16)px"
     r"[\s\S]{0,400}?border-radius:\s*(?:8|10|12|16)px",
     "the same border-radius on three or more blocks. One radius stamped on "
     "everything flattens hierarchy; spend radius by role."),
]

EMOJI = re.compile(
    r"[\U0001F300-\U0001FAFF☀-➿️]"
)


def visible_text(src):
    """Rendered text only, entities resolved. Mirrors check-copy.py."""
    s = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    s = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s).strip()


def headings(src):
    """Rendered heading text, for the emoji check."""
    out = []
    for m in re.finditer(r"<h[1-4][^>]*>(.*?)</h[1-4]>", src, re.S | re.I):
        out.append(html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip())
    return out


def scan(src, patterns):
    hits = []
    for pat, why in patterns:
        for m in re.finditer(pat, src, re.I):
            line = src[:m.start()].count("\n") + 1
            frag = re.sub(r"\s+", " ", m.group(0))[:70]
            hits.append((line, frag, why))
    return sorted(hits)


def find_pages(paths):
    pages = []
    for p in paths:
        if os.path.isfile(p):
            pages.append(p)
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs
                       if d not in {".git", ".claude", ".planning",
                                    "scripts", "fonts", "img"}]
            pages += [os.path.join(root, f) for f in files if f.endswith(".html")]
    return sorted(set(pages))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=["."])
    args = ap.parse_args()

    pages = find_pages(args.paths or ["."])
    if not pages:
        print("FAIL: no HTML pages found", file=sys.stderr)
        return 2

    print(f"Pages: {len(pages)}\n")
    fails = reviews = 0

    for page in pages:
        src = open(page, encoding="utf-8").read()

        page_fails = scan(src, FAIL)
        page_reviews = scan(src, REVIEW)

        # Dashes, entities included. The check-copy.py blind spot.
        text = visible_text(src)
        dashes = text.count("—") + text.count("–")
        if dashes:
            page_fails.append((0, f"{dashes} dash(es)",
                               "em or en dash in rendered copy. Rewrite with a "
                               "comma, a period or a conjunction."))

        # Emoji standing in for a designed mark.
        for h in headings(src):
            if EMOJI.search(h):
                page_fails.append((0, h[:50], "emoji in a heading."))

        fails += len(page_fails)
        reviews += len(page_reviews)

        status = "FAIL" if page_fails else "ok"
        print(f"[{status}] {page}")
        for line, frag, why in page_fails:
            where = f":{line}" if line else ""
            print(f"        FAIL{where}  {frag}\n              {why}")
        for line, frag, why in page_reviews:
            print(f"        review:{line}  {frag}\n              {why}")

    print()
    if fails:
        print(f"FAILED: {fails} pattern(s) with no defensible use here.")
        return 1
    if reviews:
        print(f"Clean on hard failures. {reviews} judgment call(s) above are "
              f"for a human to confirm are deliberate.")
    else:
        print("Clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
