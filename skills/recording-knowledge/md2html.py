#!/usr/bin/env python3
"""Convert a knowledge-note Markdown file to a styled HTML file (stdlib only).

Usage: python3 md2html.py note.md  -> writes note.html next to it.

Supported syntax: frontmatter, headings, paragraphs, fenced code blocks,
inline code, **bold**, *italic*, [links](url), [^footnotes], flat ul/ol lists,
blockquotes, pipe tables, horizontal rules.
"""
import html
import re
import sys
from pathlib import Path

CSS = """
body { max-width: 760px; margin: 40px auto; padding: 0 16px;
       font-family: -apple-system, "Hiragino Sans", "Hiragino Kaku Gothic ProN", Meiryo, sans-serif;
       line-height: 1.8; color: #24292f; }
h1 { border-bottom: 2px solid #d0d7de; padding-bottom: .3em; }
h2 { border-bottom: 1px solid #d0d7de; padding-bottom: .2em; margin-top: 2em; }
code { background: #eff1f3; padding: .15em .4em; border-radius: 6px;
       font-family: ui-monospace, Menlo, monospace; font-size: .9em; }
pre { background: #0d1117; color: #e6edf3; padding: 16px; border-radius: 8px; overflow-x: auto; }
pre code { background: none; color: inherit; padding: 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #d0d7de; padding: 6px 13px; }
th { background: #f6f8fa; }
blockquote { border-left: 4px solid #d0d7de; margin: 0; padding: 0 16px; color: #57606a; }
a { color: #0969da; }
hr { border: none; border-top: 1px solid #d0d7de; }
.footnotes { font-size: .9em; color: #57606a; }
.footnotes sup { font-size: inherit; }
"""


def parse_frontmatter(text):
    """Return (frontmatter_dict, body)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    fm = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm, text[end + 4 :]


_footnotes = {"order": [], "defs": {}, "counts": {}}


def parse_footnotes(md):
    """Extract `[^label]: text` definitions; return (defs, body_without_defs)."""
    defs, body = {}, []
    for line in md.split("\n"):
        m = re.match(r"^\[\^([^\]]+)\]:[ \t]?(.*)$", line)
        if m:
            defs[m.group(1)] = m.group(2)
        else:
            body.append(line)
    return defs, "\n".join(body)


def _footnote_sub(m):
    label = m.group(1)
    if label not in _footnotes["defs"]:
        return m.group(0)
    if label not in _footnotes["order"]:
        _footnotes["order"].append(label)
    n = _footnotes["order"].index(label) + 1
    _footnotes["counts"][n] = _footnotes["counts"].get(n, 0) + 1
    rid = f"ref{n}" if _footnotes["counts"][n] == 1 else f"ref{n}-{_footnotes['counts'][n]}"
    return f'<sup id="{rid}"><a href="#fn{n}">[{n}]</a></sup>'


def _link_sub(m):
    text, href = m.group(1), m.group(2)
    if href.endswith(".md") and not re.match(r"^[a-zA-Z]+://", href):
        parts = href.split("/")
        stem = parts[-1][:-3]
        if stem == "README" or stem.startswith("README-"):
            parts[-1] = "index" + stem[len("README"):] + ".html"
        else:
            parts[-1] = stem + ".html"
        href = "/".join(parts)
    return f'<a href="{href}">{text}</a>'


def inline(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link_sub, text)
    text = re.sub(r"\[\^([^\]]+)\]", _footnote_sub, text)
    return text


def render_table(rows):
    def cells(row):
        return [c.strip() for c in row.strip().strip("|").split("|")]

    def is_separator(row):
        return bool(re.match(r"^\|?[\s:|-]+\|?$", row)) and "-" in row

    header = cells(rows[0])
    body = [cells(r) for r in rows[1:] if not is_separator(r)]
    th = "".join(f"<th>{inline(c)}</th>" for c in header)
    trs = "".join(
        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


LIST_RE = re.compile(r"^\s*([-*+]|\d+\.)\s+(.*)$")


def render(md):
    defs, md = parse_footnotes(md)
    _footnotes.update(order=[], defs=defs, counts={})
    lines = md.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if m := re.match(r"^```(\w*)\s*$", line):
            lang, buf, i = m.group(1), [], i + 1
            while i < len(lines) and not re.match(r"^```\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = f' class="language-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(buf))}</code></pre>")
            continue
        if not line.strip():
            i += 1
            continue
        if m := re.match(r"^(#{1,6})\s+(.*)$", line):
            lv = len(m.group(1))
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,})\s*$", line):
            out.append("<hr>")
            i += 1
            continue
        if line.lstrip().startswith("|"):
            tbl = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            out.append(render_table(tbl))
            continue
        if line.lstrip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(
                "<blockquote><p>" + "<br>\n".join(inline(b) for b in buf) + "</p></blockquote>"
            )
            continue
        if m := LIST_RE.match(line):
            tag = "ol" if re.match(r"\d+\.", m.group(1)) else "ul"
            items = []
            while i < len(lines) and (mm := LIST_RE.match(lines[i])):
                items.append(f"<li>{inline(mm.group(2))}</li>")
                i += 1
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue
        buf = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip() or re.match(
                r"^(#{1,6}\s|```|\s*>|\s*[-*+]\s|\s*\d+\.\s|\s*\||-{3,}\s*$|\*{3,}\s*$)", nxt
            ):
                break
            buf.append(nxt)
            i += 1
        out.append("<p>" + "<br>\n".join(inline(b) for b in buf) + "</p>")
    if _footnotes["order"]:
        lis = "".join(
            f'<li id="fn{n}">{inline(_footnotes["defs"][label])} '
            f'<a href="#ref{n}">&#8617;</a></li>'
            for n, label in enumerate(_footnotes["order"], 1)
        )
        out.append(f'<section class="footnotes"><hr><ol>{lis}</ol></section>')
    return "\n".join(out)


def output_path(src):
    """README.md -> index.html, README-en.md -> index-en.html, otherwise <name>.html."""
    stem = src.stem
    if stem == "README" or stem.startswith("README-"):
        return src.with_name("index" + stem[len("README"):] + ".html")
    return src.with_suffix(".html")


def main():
    src = Path(sys.argv[1])
    fm, body = parse_frontmatter(src.read_text(encoding="utf-8"))
    title = fm.get("title") or src.parent.name if src.stem == "README" else fm.get("title") or src.stem
    meta_parts = [x for x in [fm.get("date"), fm.get("tags")] if x]
    meta = f'<p><small>{html.escape(" / ".join(meta_parts))}</small></p>' if meta_parts else ""
    page = (
        "<!DOCTYPE html>\n<html lang=\"ja\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        f"{meta}\n{render(body)}\n</body>\n</html>\n"
    )
    dst = output_path(src)
    dst.write_text(page, encoding="utf-8")
    print(dst)


if __name__ == "__main__":
    main()
