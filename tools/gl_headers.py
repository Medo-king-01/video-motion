#!/usr/bin/env python3
"""Inventory of what each shader in `assets/gl-transitions/` says about itself.

Reads the comment header of every `*.glsl` file — `// Author:`, `// License:`, and any line that
points at another origin (a URL, "ported from", "based on", a copyright line) — and writes the
table `docs/gl-transitions-headers.md`. It reports what the files declare. It does not check the
upstream repository and it does not decide what any licence permits.

    python3 tools/gl_headers.py            print the summary
    python3 tools/gl_headers.py --write    regenerate the table, THIRD_PARTY.md and MANIFEST.json
    python3 tools/gl_headers.py --check    exit 1 if any of the three no longer matches the files

Next to the shaders it also writes `THIRD_PARTY.md` (the full notice of every file that declares a
licence other than MIT, copied from the file) and `MANIFEST.json` (one entry per file with its
sha256). What is not known — the upstream commit the files were copied from — is written as
"غير معروف", never guessed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "assets" / "gl-transitions"
OUT = ROOT / "docs" / "gl-transitions-headers.md"

AUTHOR = re.compile(r"^\s*//\s*Author\s*:\s*(.+?)\s*$", re.I)
LICENCE = re.compile(r"^\s*//\s*Licen[sc]e\s*:\s*(.+?)\s*$", re.I)
ORIGIN = re.compile(r"https?://|copyright|\b(ported|adapted|forked|converted|based on|inspired by|copied)\b"
                    r"|licen[sc]e|redistribut|with credit", re.I)
DESCRIPTIVE = re.compile(r"^\s*//\s*(Description|Tags)\s*:", re.I)
BOILERPLATE = re.compile(r"redistributions? (of|in)|this software is provided|neither the name|"
                         r"copyright notice, this list|redistribution and use", re.I)
URL = re.compile(r"https?://[^\s)>\]]+")
COMMON = "MIT"
UNKNOWN = "غير معروف"
UNDECIDED = "غير محسوم"
BLOCKED = "غير صالح لإعادة التوزيع قبل مراجعة"
NOT_REVIEWED = "لم يُراجَع"

# Observed once, by hand, from the public repository — a record of what was seen, not a ruling.
# Re-observe and edit here; nothing in this tool touches the network.
UPSTREAM = {
    "repository": "https://github.com/gl-transitions/gl-transitions",
    "observed_on": "2026-11-11",
    "observed_at_commit": "1fe42183109f1585efb7a282c9b6b1c459cd548f",
    "licence_file": {"path": "LICENSE", "git_blob": "7a1f053650848112e9448f829b3a5c81ea405e45"},
    "licence_reported_by_github": "NOASSERTION",
    "readme_statement": "Each transition states its license in its header, and the packages give it with "
                        "each transition: all are MIT except two under BSD licenses.",
    "transitions_upstream_at_that_commit": 214,
    "files_here_identical_to_that_commit": 181,
    "files_here_that_differ_from_that_commit": ["BookFlip.glsl", "Cube.glsl", "Doorway.glsl", "GridFlip.glsl",
                                                "HeartWipe.glsl", "Shatter.glsl", "Swirl.glsl", "WaterDrop.glsl"],
}
UPSTREAM_LICENCE_TEXT = """\
MIT License

Copyright (c) 2017-present gl-transitions contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Note: Individual transitions in the transitions/ directory may have their own
license specified in their file header comments. When no license is specified,
the transition is covered by this MIT license."""



def inventory(store: Path = STORE) -> list[dict]:
    rows = []
    for path in sorted(store.glob("*.glsl")):
        authors, licences, origins = [], [], []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if DESCRIPTIVE.match(line):
                continue
            if found := AUTHOR.match(line):
                authors.append(found.group(1))
            elif found := LICENCE.match(line):
                licences.append(found.group(1))
            elif ORIGIN.search(line) and not BOILERPLATE.search(line):
                origins.append(re.sub(r"^[\s/*]+|[\s/*]+$", "", line))
        distinct = list(dict.fromkeys(licences))
        flags = []
        if not licences:
            flags.append("no licence line")
        elif any(item.upper() != COMMON for item in distinct):
            flags.append("not MIT")
        if len(licences) > 1:
            flags.append("more than one licence line")
        if any("copyright" in item.lower() for item in origins):
            flags.append("carries its own copyright notice")
        if any(URL.search(item) or re.search(r"based on|ported|adapted|forked|converted|copied", item, re.I)
               for item in origins):
            flags.append("names another origin")
        rows.append({"file": path.name, "author": " · ".join(authors), "licence": " · ".join(distinct),
                     "origin": " ⏎ ".join(origins), "flag": ", ".join(flags),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return rows


def notice(path: Path) -> str:
    """The licence notice a shader carries, from its copyright line to the end of the disclaimer,
    with the comment markers removed and nothing else changed. Empty when the file has none."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    starts = [i for i, line in enumerate(lines) if "Copyright (c)" in line]
    ends = [i for i, line in enumerate(lines) if "DAMAGE." in line]
    if not starts or not ends or ends[-1] < starts[0]:
        return ""
    return "\n".join(re.sub(r"^\s*//\s?", "", line).rstrip() for line in lines[starts[0]:ends[-1] + 1])


def third_party(rows: list[dict], store: Path = STORE) -> str:
    out = [
        "# gl-transitions — third-party notices",
        "",
        "<!-- generated by tools/gl_headers.py --write; do not edit by hand -->",
        "",
        "The shaders in this folder were written by many authors. Each file states its own licence in",
        "its header. This file gathers, word for word, the notice of every file that declares a licence",
        f"other than MIT, so the notice travels with the folder. Status of the licence review: **{UNDECIDED}**",
        "(undecided) — nothing here says what may be done with the files.",
        "",
        "Per-file list: `MANIFEST.json` here and `docs/gl-transitions-headers.md`.",
        "",
    ]
    for row in rows:
        if not row["licence"] or all(item.strip().upper() == COMMON for item in row["licence"].split("·")):
            continue
        text = notice(store / row["file"])
        out += [f"## `{row['file']}` — declares: {row['licence']}", "",
                f"Author line: {row['author'] or UNKNOWN}", "",
                "```text", text or f"({UNKNOWN}: the file names this licence but carries no notice text)", "```", ""]
    out += [
        "## Upstream `LICENSE` file — as observed, not as applied",
        "",
        f"Seen in {UPSTREAM['repository']} on {UPSTREAM['observed_on']} at commit",
        f"`{UPSTREAM['observed_at_commit']}`. The commit these files were copied from is **{UNKNOWN}**",
        "(unknown), so whether this text is the one that applied to them then is not established;",
        f"{len(UPSTREAM['files_here_that_differ_from_that_commit'])} of the files here differ from that commit.",
        "",
        "```text", UPSTREAM_LICENCE_TEXT.rstrip("\n"), "```",
    ]
    return "\n".join(out) + "\n"


def manifest(rows: list[dict]) -> str:
    data = {
        "generated_by": "tools/gl_headers.py --write",
        "what_this_is": "what each file declares about itself, plus its sha256 — not a licence decision",
        "review_status": UNDECIDED,
        "imported_from_commit": UNKNOWN,
        "imported_on": UNKNOWN,
        "upstream_as_observed": UPSTREAM,
        "files": [{
            "file": row["file"], "sha256": row["sha256"], "author": row["author"] or UNKNOWN,
            "declared_licence": row["licence"] or UNKNOWN, "other_origin_named": row["origin"],
            "listed_for_review_because": row["flag"],
            "redistribution": BLOCKED if row["flag"] else NOT_REVIEWED,
        } for row in rows],
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _cell(text: str, limit: int = 220) -> str:
    text = text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summary(rows: list[dict]) -> list[str]:
    by_licence = collections.Counter(row["licence"] or "(none declared)" for row in rows)
    lines = [f"- `{name}`: {count}" for name, count in sorted(by_licence.items(), key=lambda kv: (-kv[1], kv[0]))]
    return lines


def render(rows: list[dict]) -> str:
    odd = [row for row in rows if row["flag"]]
    out = [
        "# gl-transitions — what each file declares",
        "",
        "<!-- generated by tools/gl_headers.py --write; do not edit by hand -->",
        "",
        "Read from the comment header of each file in `assets/gl-transitions/`. This is a transcript of",
        "what the files say, **not a licence decision**: nobody has compared it with the upstream",
        "repository or judged what the terms require. Status: **غير محسوم** (undecided).",
        "",
        f"Files: {len(rows)}. Declared licence:",
        "",
        *summary(rows),
        "",
        f"## Files that need a look ({len(odd)})",
        "",
        "Anything other than a single `License: MIT` line with no other origin named. Every file in this",
        f"table is marked **{BLOCKED}** (not to be redistributed before a review); the remaining files are",
        f"{NOT_REVIEWED} (not reviewed) — that is not a clearance either.",
        "",
        "| File | Author | Declared licence | Why it is listed | Redistribution | Other origin named in the file |",
        "|---|---|---|---|---|---|",
    ]
    out += [f"| `{r['file']}` | {_cell(r['author'])} | {_cell(r['licence']) or '—'} | {r['flag']} | **{BLOCKED}** | "
            f"{_cell(r['origin']) or '—'} |" for r in odd]
    out += ["", f"## All files ({len(rows)})", "", "| File | Author | Declared licence | Listed above |", "|---|---|---|---|"]
    out += [f"| `{r['file']}` | {_cell(r['author']) or '—'} | {_cell(r['licence']) or '—'} | {'yes' if r['flag'] else ''} |"
            for r in rows]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="regenerate the table")
    parser.add_argument("--check", action="store_true", help="fail if the table is out of date")
    parser.add_argument("--store", type=Path, default=STORE, help=argparse.SUPPRESS)
    parser.add_argument("--out", type=Path, default=OUT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    rows = inventory(args.store)
    outputs = {args.out: render(rows), args.store / "THIRD_PARTY.md": third_party(rows, args.store),
               args.store / "MANIFEST.json": manifest(rows)}
    if args.write:
        for path, text in outputs.items():
            path.write_text(text, encoding="utf-8")
        print(f"OK wrote {', '.join(path.name for path in outputs)}: {len(rows)} files, "
              f"{sum(1 for r in rows if r['flag'])} listed for a look")
        return 0
    if args.check:
        stale = [path.name for path, text in outputs.items()
                 if not path.is_file() or path.read_text(encoding="utf-8") != text]
        if stale:
            print(f"FAIL {', '.join(stale)} do not match the shader files — run: python3 tools/gl_headers.py --write")
            return 1
        print(f"OK {', '.join(path.name for path in outputs)} match {len(rows)} shader files")
        return 0
    print(f"{len(rows)} files")
    print("\n".join(summary(rows)))
    for row in rows:
        if row["flag"]:
            print(f"  {row['file']}: {row['flag']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
