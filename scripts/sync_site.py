#!/usr/bin/env python3
"""Refresh the README's certifications, projects and writing sections from the
blog's source repo (sneakywarwolf/sneakywarwolf.github.io).

Sources (read from the repo, not scraped from the rendered site):
  certifications  _tabs/about.md, bullets under "## Certifications"
  projects        _data/projects.yml
  writing         _posts/*.md front matter (latest POSTS_SHOWN published posts)

Each section is rewritten between <!-- SITE:<NAME>:START --> / END markers.

    pip install pyyaml
    python3 scripts/sync_site.py            # set GITHUB_TOKEN to avoid API rate limits
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import yaml

REPO = "sneakywarwolf/sneakywarwolf.github.io"
BRANCH = "main"
SITE = "https://sneakywarwolf.github.io"
README = "README.md"
POSTS_SHOWN = 5


def fetch(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-sync"})
    if accept:
        req.add_header("Accept", accept)
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def raw(path):
    return fetch(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{urllib.parse.quote(path)}")


def front_matter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def shield(text):
    return urllib.parse.quote(text.replace("-", "--").replace("_", "__").replace(" ", "_"), safe="()")


# ---------------------------------------------------------------- sections

def certifications():
    about = raw("_tabs/about.md")
    m = re.search(r"^##\s+Certifications\s*\n(.*?)(?=^##\s|\Z)", about, re.S | re.M)
    if not m:
        raise SystemExit("Certifications heading not found in _tabs/about.md")
    items = [l[2:].strip() for l in m.group(1).splitlines() if l.startswith("- ")]
    badges = []
    for item in items:
        left, _, right = (s.strip() for s in item.partition(" - "))
        path = f"{shield(left)}-{shield(right)}" if right else shield(left)
        badges.append(f'<img src="https://img.shields.io/badge/{path}-0d1117?style=for-the-badge" alt="{item}">')
    return "\n".join(badges)


def projects():
    rows = ["| Project | What it does | Stack |", "| :--- | :--- | :--- |"]
    for p in yaml.safe_load(raw("_data/projects.yml")) or []:
        name, repo = p.get("name", ""), p.get("repo", "")
        link = f"[**{name}**](https://github.com/{repo})" if repo else f"**{name}**"
        summary = " ".join(str(p.get("summary", "")).split()).replace("|", "\\|")
        tags = " ".join(f"`{t}`" for t in p.get("tags", []))
        rows.append(f"| {link} | {summary} | {tags} |")
    return "\n".join(rows)


def slugify(name):
    """Jekyll's :title for posts ('pretty' mode, cased): keep [A-Za-z0-9._~!$&'()+,;=@], else '-'."""
    s = re.sub(r"[^A-Za-z0-9._~!$&'()+,;=@]+", "-", name)
    return re.sub(r"^-|-$", "", s)


def url_ok(url):
    """True/False when the site answers; None when it can't be reached (keep the link)."""
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20)
        return True
    except urllib.error.HTTPError as e:
        return e.code < 400
    except Exception:
        return None


def writing():
    listing = json.loads(fetch(f"https://api.github.com/repos/{REPO}/contents/_posts?ref={BRANCH}"))
    now = dt.datetime.now(dt.timezone.utc)
    posts = []
    for f in listing:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.(md|markdown)$", f["name"])
        if not m:
            continue
        fm = front_matter(raw(f"_posts/{f['name']}"))
        if fm.get("published") is False or fm.get("hidden"):
            continue
        date = fm.get("date") or m.group(1)
        if isinstance(date, str):
            date = dt.datetime.fromisoformat(re.sub(r"\s+([+-]\d)", r"\1", date.strip()).replace(" ", "T", 1))
        if isinstance(date, dt.date) and not isinstance(date, dt.datetime):
            date = dt.datetime(date.year, date.month, date.day)
        if date.tzinfo is None:
            date = date.replace(tzinfo=dt.timezone.utc)
        if date > now:                        # Jekyll doesn't publish future-dated posts
            continue
        slug = fm.get("slug") or m.group(2)
        url = f"{SITE}/posts/{urllib.parse.quote(slugify(str(slug)))}/"
        if url_ok(url) is False:
            print(f"warn: {url} not found, linking the blog home", file=sys.stderr)
            url = SITE
        cats = fm.get("categories") or []
        cats = cats if isinstance(cats, list) else [cats]
        title = str(fm.get("title", m.group(2))).replace("|", "\\|")
        posts.append((date, title, url, " / ".join(map(str, cats))))
    posts.sort(reverse=True)
    rows = ["| Post | Date | Topic |", "| :--- | :---: | :--- |"]
    rows += [f"| [{t}]({u}) | {d:%Y-%m-%d} | {c} |" for d, t, u, c in posts[:POSTS_SHOWN]]
    return "\n".join(rows)


# ---------------------------------------------------------------- main

def replace(text, name, body):
    pat = re.compile(rf"(<!-- SITE:{name}:START -->\n).*?(<!-- SITE:{name}:END -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"markers for {name} not found in {README}")
    return pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)


def main():
    text = open(README, encoding="utf-8").read()
    new = text
    for name, fn in (("CERTS", certifications), ("PROJECTS", projects), ("WRITING", writing)):
        new = replace(new, name, fn())
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print("README updated")
    else:
        print("README already up to date")


if __name__ == "__main__":
    main()
