#!/usr/bin/env python3.11
"""
Extract notebook outputs into a folder readable by Claude.

Usage:
    python3.11 research/extract_notebook.py <notebook.ipynb> [output_dir]

Produces:
    <output_dir>/
        summary.md     — all text outputs + cell sources (index for Claude)
        fig_01_*.png   — each Plotly figure as a static image
        fig_02_*.png
        ...
"""

import sys
import json
import re
import base64
import textwrap
from pathlib import Path

import plotly.io as pio
import plotly.graph_objects as go


# ── helpers ──────────────────────────────────────────────────────────────────

def _slug(text: str, maxlen: int = 40) -> str:
    """Turn arbitrary text into a safe filename fragment."""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_-]+", "_", s).strip("_")
    return s[:maxlen] or "fig"


def _extract_json_arg(html: str, start: int) -> str | None:
    """
    Starting at `start` (which should be '[' or '{'), extract the full
    JSON value by tracking bracket depth, handling strings and escapes.
    """
    if start >= len(html) or html[start] not in "{[":
        return None
    opener = html[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(html)):
        c = html[i]
        if esc:
            esc = False
            continue
        if c == "\\" and in_str:
            esc = True
            continue
        if c == '"' and not esc:
            in_str = not in_str
            continue
        if in_str:
            continue
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return html[start : i + 1]
    return None


def _extract_plotly_from_html(html: str):
    """
    Pull the Plotly figure out of fig.to_html() output.
    Handles plotly 5.x  : Plotly.newPlot("id", [traces], {layout}, ...)
    Handles plotly 6.x  : Plotly.newPlot("id", {figure},  ...)
    Returns a go.Figure or None.
    """
    for func in ("Plotly.newPlot(", "Plotly.react("):
        idx = html.find(func)
        if idx == -1:
            continue
        # skip past opening paren
        pos = html.index("(", idx) + 1
        # skip the UUID string argument
        while pos < len(html) and html[pos] in " \t\n\r":
            pos += 1
        if pos < len(html) and html[pos] in "\"'":
            q = html[pos]
            pos += 1
            while pos < len(html) and html[pos] != q:
                pos += 1
            pos += 1  # closing quote
        # skip comma + whitespace
        while pos < len(html) and html[pos] in ", \t\n\r":
            pos += 1

        raw1 = _extract_json_arg(html, pos)
        if raw1 is None:
            continue
        try:
            obj1 = json.loads(raw1)
        except Exception:
            continue

        # plotly 6.x: second arg is full figure dict
        if isinstance(obj1, dict) and ("data" in obj1 or "layout" in obj1):
            try:
                return pio.from_json(raw1)
            except Exception:
                return go.Figure(obj1)

        # plotly 5.x: second arg is traces list; third is layout dict
        if isinstance(obj1, list):
            pos2 = pos + len(raw1)
            while pos2 < len(html) and html[pos2] in ", \t\n\r":
                pos2 += 1
            raw2 = _extract_json_arg(html, pos2)
            layout = {}
            if raw2:
                try:
                    layout = json.loads(raw2)
                except Exception:
                    pass
            return go.Figure(data=obj1, layout=layout)

    return None


def _fig_to_png(fig: go.Figure, path: Path, title: str = ""):
    if title:
        fig.update_layout(title_text=title)
    fig.write_image(str(path), scale=2, width=1200, height=fig.layout.height or 450)


# ── main extraction ───────────────────────────────────────────────────────────

def extract(nb_path: str, out_dir: str | None = None):
    nb_path = Path(nb_path)
    if out_dir is None:
        out_dir = nb_path.parent / (nb_path.stem + "_export")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(nb_path) as f:
        nb = json.load(f)

    cells = nb["cells"]
    md_lines = [
        f"# {nb_path.stem} — extracted outputs\n",
        f"Source: `{nb_path}`\n",
        "---\n",
    ]

    fig_counter = 0
    skipped_figs = 0

    for cell_idx, cell in enumerate(cells):
        src = "".join(cell.get("source", []))
        outputs = cell.get("outputs", [])

        if not src.strip() and not outputs:
            continue

        # ── section heading from markdown cells ──────────────────────────────
        if cell["cell_type"] == "markdown":
            md_lines.append(src.strip() + "\n\n")
            continue

        # ── code cell: emit source as collapsed block ─────────────────────────
        has_output = bool(outputs)
        if src.strip():
            md_lines.append(f"```python\n{src.strip()}\n```\n\n")

        # ── process outputs ───────────────────────────────────────────────────
        for out in outputs:
            otype = out.get("output_type", "")

            # --- text / stream ---
            if otype == "stream":
                text = "".join(out.get("text", []))
                if text.strip():
                    md_lines.append("**Output:**\n```\n" + text.rstrip() + "\n```\n\n")

            # --- execute_result (repr, dataframe HTML, etc.) ---
            elif otype == "execute_result":
                data = out.get("data", {})
                if "text/plain" in data:
                    txt = "".join(data["text/plain"])
                    md_lines.append("**Result:**\n```\n" + txt.rstrip() + "\n```\n\n")

            # --- display_data: PNG / Plotly HTML / Plotly JSON ---
            elif otype == "display_data":
                data = out.get("data", {})

                # Already a PNG (e.g. renderer='png')
                if "image/png" in data:
                    fig_counter += 1
                    title = _slug(src.split("\n")[0], 40)
                    fname = f"fig_{fig_counter:02d}_{title}.png"
                    img_bytes = base64.b64decode(data["image/png"])
                    (out_dir / fname).write_bytes(img_bytes)
                    md_lines.append(f"![{fname}]({fname})\n\n")

                # Plotly JSON (notebook / notebook_connected renderer)
                elif "application/vnd.plotly.v1+json" in data:
                    fig_counter += 1
                    title = _slug(src.split("\n")[0], 40)
                    fname = f"fig_{fig_counter:02d}_{title}.png"
                    try:
                        fig_json = json.dumps(data["application/vnd.plotly.v1+json"])
                        fig = pio.from_json(fig_json)
                        _fig_to_png(fig, out_dir / fname, title="")
                        md_lines.append(f"![{fname}]({fname})\n\n")
                    except Exception as e:
                        md_lines.append(f"_(figure {fig_counter} — render failed: {e})_\n\n")
                        skipped_figs += 1

                # HTML with embedded Plotly (our custom show() function)
                elif "text/html" in data:
                    html = "".join(data["text/html"])
                    if "Plotly" in html or "plotly" in html:
                        fig_counter += 1
                        title = _slug(src.split("\n")[0], 40)
                        fname = f"fig_{fig_counter:02d}_{title}.png"
                        fig = _extract_plotly_from_html(html)
                        if fig is not None:
                            try:
                                _fig_to_png(fig, out_dir / fname)
                                md_lines.append(f"![{fname}]({fname})\n\n")
                            except Exception as e:
                                md_lines.append(f"_(figure {fig_counter} — render failed: {e})_\n\n")
                                skipped_figs += 1
                        else:
                            md_lines.append(f"_(figure {fig_counter} — could not parse HTML)_\n\n")
                            skipped_figs += 1
                    else:
                        # Plain HTML table etc — grab text/plain fallback
                        if "text/plain" in data:
                            txt = "".join(data["text/plain"])
                            md_lines.append("```\n" + txt.rstrip() + "\n```\n\n")

    # ── write summary ─────────────────────────────────────────────────────────
    summary_path = out_dir / "summary.md"
    summary_path.write_text("".join(md_lines), encoding="utf-8")

    print(f"Done → {out_dir}/")
    print(f"  summary.md")
    print(f"  {fig_counter - skipped_figs} figures saved as PNG")
    if skipped_figs:
        print(f"  {skipped_figs} figures skipped (parse/render error)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    extract(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
