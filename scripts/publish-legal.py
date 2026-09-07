#!/usr/bin/env python3
"""Focused legal-page publisher for pushingpeak.app (recreates Phase 43-04's converter).

Converts the app repo's `legal/terms.md` and `legal/privacy.md` VERBATIM — no clause
dropped, no clause added — into the body of `terms/index.html` / `privacy/index.html`,
preserving each page's existing <head>/<style> chrome and footer line untouched.

Usage:  python3 scripts/publish-legal.py <path-to-app-repo>/legal
Then:   review `git diff`, commit, push. The pages are hand-served static HTML
        (`.nojekyll`); nothing else publishes them.

Supported markdown (the full feature set these two documents use):
#/## headings · **bold** · *italic* · `code` · [text](url) · - bullet lists with
continuation lines · pipe tables · paragraphs. Anything else is passed through as
escaped text, which will be visible in review — by design, never silently dropped.
"""
import html, re, sys, pathlib

def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'(?<![">])(https://pushingpeak\.app[^\s<]*[^\s<.,)])',
               r'<a href="\1">\1</a>', s)
    return s

def convert(md: str) -> tuple[str, str]:
    lines = md.split('\n')
    out, para, bullets, table = [], [], [], []
    title = ''

    def flush_para():
        nonlocal para
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>')
            para = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            out.append('<ul>')
            out.extend('<li>' + inline(b) + '</li>' for b in bullets)
            out.append('</ul>')
            bullets = []

    def flush_table():
        nonlocal table
        if table:
            head = [c.strip() for c in table[0].strip('|').split('|')]
            out.append('<table>')
            out.append('<tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr>')
            for row in table[2:]:
                cells = [c.strip() for c in row.strip('|').split('|')]
                out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells) + '</tr>')
            out.append('</table>')
            table = []

    def flush_all():
        flush_para(); flush_bullets(); flush_table()

    for raw in lines:
        line = raw.rstrip()
        if line.startswith('# ') and not title:
            title = line[2:].strip(); flush_all()
        elif line.startswith('## '):
            flush_all(); out.append('<h2>' + inline(line[3:].strip()) + '</h2>')
        elif line.startswith('|'):
            flush_para(); flush_bullets(); table.append(line)
        elif line.startswith('- '):
            flush_para(); flush_table(); bullets.append(line[2:].strip())
        elif line.startswith('  ') and bullets and line.strip():
            bullets[-1] += ' ' + line.strip()
        elif not line.strip():
            flush_all()
        else:
            flush_bullets(); flush_table(); para.append(line.strip())
    flush_all()
    return title, '\n'.join(out)

def publish(md_path: pathlib.Path, html_path: pathlib.Path) -> None:
    """Replace the page's <main> content. Everything outside it is the page's
    own chrome and is preserved verbatim, in both directions.

    THE TAIL USED TO BE HARDCODED as '</main></body></html>', which meant any
    wrapper closing after </main> was silently destroyed on the next publish.
    That made it impossible for these pages to carry the site chrome, which
    closes a .wrap and a .top-fade after </main>. Now the tail is preserved the
    same way the head always was, so the chrome is the page's to own and this
    script only ever owns what is between the <main> tags.
    """
    title, body = convert(md_path.read_text())
    page = html_path.read_text()
    head, sep, tail = page.partition('<main>')
    assert sep, f'{html_path}: no <main>'
    close = tail.find('</main>')
    assert close != -1, f'{html_path}: no </main>'
    after = tail[close + len('</main>'):]          # chrome, preserved
    footer_match = re.search(r'<p class="footer">.*?</p>', tail[:close], re.S)
    assert footer_match, f'{html_path}: no footer'
    # The h1 goes in .page-hero so these pages open the way every other page
    # does: a centred heading over the fade.
    new_main = (f'\n<div class="page-hero"><h1>{html.escape(title, quote=False)}</h1></div>\n'
                f'{body}\n{footer_match.group(0)}\n</main>')
    html_path.write_text(head + sep + new_main + after)
    print(f'{html_path.name}: rebuilt from {md_path.name} ({len(body.splitlines())} body lines)')

if __name__ == '__main__':
    legal = pathlib.Path(sys.argv[1])
    site = pathlib.Path(__file__).resolve().parent.parent
    publish(legal / 'terms.md', site / 'terms' / 'index.html')
    publish(legal / 'privacy.md', site / 'privacy' / 'index.html')
