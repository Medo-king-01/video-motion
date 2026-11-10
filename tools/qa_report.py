#!/usr/bin/env python3
"""One HTML page for the visual QA of a reel: lint + Final Media QA + a contact sheet.

    python3 tools/qa_report.py projects/my-reel --media projects/my-reel/out/master.mp4
    # writes projects/my-reel/out/qa/report.html (self-contained: no network, no external files)

The terminal tells you `Q03: Unintended black frame run(s)`; this page shows the frame, the
lint findings next to the media findings, and the thresholds that were applied, so a human can
judge a cut without replaying the whole reel. Arabic-first, right-to-left, printable.

Exit codes: 0 when the page was written (even if the media fails QA — that is the page's job),
2 when the tool could not run (missing media, unwritable output, broken JSON).
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))

import media_qa  # noqa: E402

STATUS_LABEL = {
    "pass": ("نجح", "#1f7a3d"),
    "fail": ("فشل", "#b3261e"),
    "incomplete": ("ناقص", "#8a5a00"),
}
LEVEL_LABEL = {"error": "خطأ", "warn": "تحذير", "ok": "سليم"}


def lint_project(project: Path, scratch: Path) -> tuple[dict[str, Any] | None, str]:
    """Run `reel_lint --json`; return (payload, human text). Never fatal."""
    target = scratch / "lint.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "reel_lint.py"), str(project), "--json", str(target)],
        capture_output=True, text=True, check=False,
    )
    payload = None
    if target.is_file():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = None
    return payload, (result.stdout + result.stderr).strip()


def collect(project: Path, media: Path, *, mode: str, sheet: Path) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    beats = project / "plan" / "beats.json"
    vo = project / "out" / "vo24.wav"
    report = media_qa.inspect_media(
        media,
        mode=mode,
        vo_path=vo if vo.is_file() else None,
        beats_path=beats if beats.is_file() else None,
        sheet_path=sheet,
    )
    with tempfile.TemporaryDirectory(prefix="qa-report-") as scratch:
        lint, lint_text = lint_project(project, Path(scratch))
    return report, lint, lint_text


def _image_data_uri(path: Path) -> str | None:
    if not path.is_file():
        return None
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _items_rows(items: list[dict[str, str]]) -> str:
    rows = []
    for item in items:
        colour = {"error": "#b3261e", "warn": "#8a5a00", "ok": "#1f7a3d"}.get(item["level"], "#444")
        rows.append(
            f"<tr><td dir=\"ltr\">{_esc(item['code'])}</td>"
            f"<td style=\"color:{colour};font-weight:600\">{_esc(LEVEL_LABEL.get(item['level'], item['level']))}</td>"
            f"<td>{_esc(item['msg'])}</td></tr>"
        )
    return "\n".join(rows) or "<tr><td colspan=\"3\">لا توجد بنود.</td></tr>"


def _lint_rows(lint: dict[str, Any] | None, text: str) -> str:
    if not lint:
        return f"<pre class=\"raw\">{_esc(text or 'لم يُشغَّل reel_lint')}</pre>"
    issues = lint.get("issues") or lint.get("findings") or []
    if not issues:
        return "<p>reel_lint: لا ملاحظات.</p>"
    rows = []
    for issue in issues:
        if not isinstance(issue, dict):
            rows.append(f"<tr><td colspan=\"3\">{_esc(issue)}</td></tr>")
            continue
        code = issue.get("code") or issue.get("id") or ""
        level = issue.get("level") or issue.get("severity") or ""
        message = issue.get("message") or issue.get("msg") or ""
        rows.append(f"<tr><td dir=\"ltr\">{_esc(code)}</td><td>{_esc(level)}</td><td>{_esc(message)}</td></tr>")
    return "<table><thead><tr><th>الكود</th><th>المستوى</th><th>الرسالة</th></tr></thead><tbody>" \
        + "\n".join(rows) + "</tbody></table>"


def build_html(*, project: Path, media: Path, report: dict[str, Any], lint: dict[str, Any] | None,
               lint_text: str, sheet: Path) -> str:
    status = str(report.get("status", "incomplete"))
    label, colour = STATUS_LABEL.get(status, (status, "#444"))
    video = report.get("video", {})
    audio = report.get("audio", {})
    thresholds = report.get("thresholds", {})
    image = _image_data_uri(sheet)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sheet_block = (f"<img alt=\"contact sheet\" src=\"{image}\">" if image
                   else "<p>لم يُنشأ contact sheet (لا توجد إطارات مُعاينة).</p>")
    audio_status = _esc(audio.get("status", "—"))
    raw = _esc(json.dumps({"media_qa": report, "reel_lint": lint}, indent=2, ensure_ascii=False))
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>تقرير QA · {_esc(project.name)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; padding: 24px; font: 16px/1.6 "Segoe UI", Tahoma, sans-serif; color: #1c1c1e; background: #f5f4f2; }}
  header {{ display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
  h1 {{ font-size: 22px; margin: 0; }}
  .pill {{ background: {colour}; color: #fff; padding: 4px 14px; border-radius: 999px; font-weight: 700; }}
  .meta {{ color: #5b5b60; font-size: 14px; }}
  section {{ background: #fff; border: 1px solid #e2e0dc; border-radius: 12px; padding: 16px 18px; margin-top: 18px; }}
  h2 {{ font-size: 17px; margin: 0 0 10px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ text-align: right; padding: 6px 8px; border-bottom: 1px solid #eee; vertical-align: top; }}
  th {{ background: #faf9f7; }}
  img {{ max-width: 100%; border-radius: 8px; border: 1px solid #ddd; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; font-size: 14px; }}
  .grid div {{ background: #faf9f7; border: 1px solid #eee; border-radius: 8px; padding: 8px 10px; }}
  .grid b {{ display: block; color: #5b5b60; font-weight: 600; font-size: 12px; }}
  pre.raw {{ white-space: pre-wrap; font-size: 12px; max-height: 420px; overflow: auto; background: #faf9f7; padding: 10px; border-radius: 8px; }}
  footer {{ color: #5b5b60; font-size: 12px; margin-top: 18px; }}
</style>
</head>
<body>
<header>
  <h1>تقرير QA · {_esc(project.name)}</h1>
  <span class="pill">{_esc(label)}</span>
  <span class="meta">أُنشئ {_esc(generated)} · {_esc(media.name)} · وضع {_esc(report.get('mode', '—'))}</span>
</header>

<section>
  <h2>الفيديو</h2>
  <div class="grid">
    <div><b>الأبعاد</b>{_esc(video.get('width'))}×{_esc(video.get('height'))}</div>
    <div><b>FPS</b>{_esc(video.get('fps'))}</div>
    <div><b>الإطارات</b>{_esc(video.get('frames'))}</div>
    <div><b>المدة</b>{_esc(video.get('duration_s'))} ثانية</div>
    <div><b>Bitrate</b>{_esc(video.get('bitrate_mbps'))} Mbps</div>
    <div><b>faststart</b>{'نعم' if video.get('faststart') else 'لا'}</div>
    <div><b>الصوت</b>{audio_status}</div>
    <div><b>حجم الملف</b>{_esc(round(media.stat().st_size / 1_000_000, 2))} MB</div>
  </div>
</section>

<section>
  <h2>contact sheet</h2>
  {sheet_block}
</section>

<section>
  <h2>نتائج Final Media QA</h2>
  <table><thead><tr><th>الكود</th><th>المستوى</th><th>الرسالة</th></tr></thead>
  <tbody>{_items_rows(report.get('items', []))}</tbody></table>
</section>

<section>
  <h2>reel_lint</h2>
  {_lint_rows(lint, lint_text)}
</section>

<section>
  <h2>العتبات المطبّقة</h2>
  <div class="grid">
    <div><b>LUFS</b>{_esc(thresholds.get('lufs'))} ± {_esc(thresholds.get('lufs_tolerance'))}</div>
    <div><b>True peak</b>{_esc(thresholds.get('true_peak_max_dbtp'))} dBTP</div>
    <div><b>أدنى bitrate</b>{_esc(thresholds.get('min_mbps'))} Mbps</div>
    <div><b>أقصى ثبات</b>{_esc(thresholds.get('idle_hold_max_s'))} ثانية</div>
  </div>
</section>

<section>
  <h2>البيانات الخام</h2>
  <details><summary>media_qa + reel_lint (JSON)</summary><pre class="raw">{raw}</pre></details>
</section>

<footer>أداة: <span dir="ltr">tools/qa_report.py</span> · صفحة مستقلة بلا شبكة: كل الصور والأرقام مضمّنة.</footer>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--media", type=Path, required=True, help="rendered MP4 to inspect")
    parser.add_argument("--out", type=Path, default=None, help="defaults to <project>/out/qa/report.html")
    parser.add_argument("--mode", choices=("master", "preview", "video-only"), default=None)
    parser.add_argument("--force", action="store_true", help="overwrite an existing report")
    parser.add_argument("--json-out", type=Path, default=None, help="also write the raw payload here")
    args = parser.parse_args(argv)

    project = args.project.resolve()
    media = args.media.resolve()
    if not project.is_dir():
        print(f"qa_report: project not found: {project}", file=sys.stderr)
        return 2
    if not media.is_file():
        print(f"qa_report: media not found: {media}", file=sys.stderr)
        return 2
    output = (args.out or project / "out" / "qa" / "report.html").resolve()
    if output.exists() and not args.force:
        print(f"qa_report: refusing to overwrite {output} (use --force)", file=sys.stderr)
        return 2
    sheet = output.with_name("contact-sheet.png")
    if sheet.exists():
        sheet.unlink()
    output.parent.mkdir(parents=True, exist_ok=True)

    mode = args.mode or "master"
    report, lint, lint_text = collect(project, media, mode=mode, sheet=sheet)
    page = build_html(project=project, media=media, report=report, lint=lint,
                      lint_text=lint_text, sheet=sheet)
    output.write_text(page, encoding="utf-8")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps({"media_qa": report, "reel_lint": lint}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(f"QA REPORT {report.get('status', '?').upper()} · {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
