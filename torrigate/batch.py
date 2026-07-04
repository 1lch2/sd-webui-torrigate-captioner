import html
import json
import logging
import time
from pathlib import Path
from typing import Iterator, List

from PIL import Image

from .api import generate_caption

logger = logging.getLogger("ToriiGate.Batch")

# Image extensions we are willing to caption. Lower-cased, compared against
# Path.suffix.lower(). Caption files (.txt/.json) are intentionally excluded
# so re-running a batch never picks up its own previous output.
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}

# Caption types whose output should be persisted as JSON. For these the model
# is asked to emit structured JSON; we save a .json file (best-effort parsed).
JSON_CAPTION_TYPES = {"json", "json_comic", "min_structured_json"}

# Cap the rendered status table to the last N rows so a multi-thousand-image
# batch does not bloat the browser DOM on every progress yield.
MAX_TABLE_ROWS = 200


def collect_images(folder_path: str) -> List[Path]:
    """Resolve the input folder into a sorted list of image paths.

    Folder semantics:
      * Path ending in ``**`` -> recurse into all subdirectories *and* include
        images directly in the base directory (e.g. ``pic/**`` captions
        ``pic/1.jpg``, ``pic/a/2.jpg``, ``pic/b/3.jpg``).
      * Any other path (trailing slash or not) -> only images directly in that
        directory, no subdirectories (e.g. ``pic`` captions only ``pic/1.jpg``).

    Raises ``ValueError`` with a human-readable message when the path is empty,
    missing, not a directory, or contains no images.
    """
    if not folder_path or not folder_path.strip():
        raise ValueError("Input folder is empty.")

    # Strip whitespace, then trailing slashes, THEN detect **. Doing it in this
    # order makes pic/**/ resolve the same as pic/** (otherwise the trailing
    # slash hides the marker and Path would look for a literal "**" dir).
    p = folder_path.strip().rstrip("/\\")
    recursive = p.endswith("**")
    if recursive:
        p = p[:-2].rstrip("/\\")
    if not p:
        raise ValueError("Input folder is empty.")

    base_path = Path(p)
    if not base_path.exists():
        raise ValueError(f"Folder does not exist: {base_path}")
    if not base_path.is_dir():
        raise ValueError(f"Not a directory: {base_path}")

    if recursive:
        candidates = base_path.rglob("*")
    else:
        candidates = base_path.iterdir()

    files = [f for f in candidates if f.is_file() and f.suffix.lower() in IMAGE_EXTS]
    if not files:
        raise ValueError(f"No images found in '{folder_path}'.")

    return sorted(files, key=lambda f: str(f))


def output_path_for(image_path: Path, caption_type: str) -> Path:
    """Return the caption file path that corresponds to *image_path*.

    ``.json`` for JSON-emitting caption types, ``.txt`` for everything else.
    The file lives in the same directory as the image.
    """
    ext = ".json" if caption_type in JSON_CAPTION_TYPES else ".txt"
    return image_path.with_suffix(ext)


def save_caption(image_path: Path, text: str, caption_type: str) -> Path:
    """Write the caption for *image_path* next to it. Returns the output path.

    For JSON caption types the text is parsed and re-dumped so the file is
    valid, pretty-printed JSON. If the model output is not parseable we wrap
    the raw text as ``{"caption": text}`` so the file remains valid JSON while
    still honoring the json-type -> .json rule. Non-JSON types are written as
    plain text.
    """
    out_path = output_path_for(image_path, caption_type)
    if caption_type in JSON_CAPTION_TYPES:
        cleaned = _strip_code_fences(text)
        try:
            parsed = json.loads(cleaned)
            content = json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            logger.warning("[ToriiGate Batch] Model output for %s was not valid JSON; wrapping raw text.", image_path.name)
            content = json.dumps({"caption": text}, ensure_ascii=False, indent=2)
    else:
        content = text

    out_path.write_text(content, encoding="utf-8")
    return out_path


def _strip_code_fences(text: str) -> str:
    """Remove a surrounding ```...``` (or ```json...```) fence if present."""
    s = text.strip()
    if s.startswith("```"):
        # Drop the opening fence line (incl. optional language tag).
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1:]
        else:
            s = ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def render_batch_html(
    rows: list,
    total: int,
    ok: int,
    skipped: int,
    failed: int,
    elapsed: float,
    done: bool = False,
    error: str = None,
) -> str:
    """Render the batch panel as an HTML string: a totals bar + status table."""
    if error:
        return (
            "<div style='font-family:var(--font);color:#e53935;padding:8px;'>"
            f"<b>Batch error:</b> {html.escape(error)}"
            "</div>"
        )

    status_cell = {
        "ok": "<span style='color:#43a047'>✓</span>",
        "skip": "<span style='color:#fb8c00'>⊘</span>",
        "fail": "<span style='color:#e53935'>✗</span>",
    }

    shown_rows = rows
    hidden = 0
    if len(rows) > MAX_TABLE_ROWS:
        hidden = len(rows) - MAX_TABLE_ROWS
        shown_rows = rows[-MAX_TABLE_ROWS:]

    rows_html = []
    if hidden:
        rows_html.append(
            "<tr><td colspan='3' style='color:#888;font-style:italic;'>"
            f"…and {hidden} earlier entries</td></tr>"
        )
    for r in shown_rows:
        name = html.escape(r["name"])
        icon = status_cell.get(r["status"], "")
        if r["status"] == "skip":
            time_str = "<span style='color:#888'>skipped</span>"
        elif r["status"] == "fail" and r.get("detail"):
            time_str = html.escape(str(r["detail"])[:80])
        elif r.get("time") is not None:
            time_str = f"{r['time']:.1f}s"
        else:
            time_str = ""
        rows_html.append(f"<tr><td>{name}</td><td style='text-align:center'>{icon}</td><td>{time_str}</td></tr>")

    title = "Batch complete" if done else "Processing batch"
    progress = f"{ok + skipped + failed}/{total}"
    bar = (
        "<div style='display:flex;gap:16px;flex-wrap:wrap;padding:6px 0;border-bottom:1px solid #555;margin-bottom:6px;'>"
        f"<b>{html.escape(title)}</b>"
        f"<span>{progress} processed</span>"
        f"<span style='color:#43a047'>✓ {ok}</span>"
        f"<span style='color:#fb8c00'>⊘ {skipped}</span>"
        f"<span style='color:#e53935'>✗ {failed}</span>"
        f"<span>{elapsed:.1f}s</span>"
        "</div>"
    )

    table = (
        "<table style='width:100%;border-collapse:collapse;font-size:small;'>"
        "<thead><tr><th style='text-align:left'>File</th>"
        "<th style='text-align:center'>Status</th>"
        "<th style='text-align:left'>Time / Note</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table>"
    )
    return bar + table


def run_batch(
    folder_path: str,
    overwrite: bool,
    caption_type: str,
    prompt: str,
    server_url: str,
    model_name: str,
    timeout: float,
    max_pixels_mp: float,
    max_new_tokens: int,
    temperature: float,
) -> Iterator[str]:
    """Caption every image in *folder_path*, yielding HTML progress strings.

    The *prompt* is image-independent and is built once by the caller. Each
    image is loaded, captioned via :func:`generate_caption`, and the result is
    saved next to it. Per-image failures are recorded but do not abort the run.
    """
    try:
        files = collect_images(folder_path)
    except ValueError as exc:
        yield render_batch_html([], 0, 0, 0, 0, 0.0, done=True, error=str(exc))
        return

    total = len(files)
    rows = []
    ok = skipped = failed = 0
    start = time.perf_counter()

    yield render_batch_html(rows, total, ok, skipped, failed, time.perf_counter() - start)

    for path in files:
        out_path = output_path_for(path, caption_type)
        if not overwrite and out_path.exists():
            rows.append({"name": path.name, "status": "skip", "time": None})
            skipped += 1
            yield render_batch_html(rows, total, ok, skipped, failed, time.perf_counter() - start)
            continue

        t0 = time.perf_counter()
        try:
            with Image.open(path) as img:
                img.load()
                result = generate_caption(
                    image=img,
                    prompt=prompt,
                    server_url=server_url,
                    model_name=model_name,
                    timeout=timeout,
                    max_pixels_mp=max_pixels_mp,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                )
            save_caption(path, result, caption_type)
            rows.append({"name": path.name, "status": "ok", "time": time.perf_counter() - t0})
            ok += 1
        except Exception as exc:
            import traceback

            logger.exception("[ToriiGate Batch] Failed to caption %s", path)
            traceback.print_exc()
            rows.append({
                "name": path.name,
                "status": "fail",
                "time": None,
                "detail": str(exc),
            })
            failed += 1

        yield render_batch_html(rows, total, ok, skipped, failed, time.perf_counter() - start)

    yield render_batch_html(rows, total, ok, skipped, failed, time.perf_counter() - start, done=True)
