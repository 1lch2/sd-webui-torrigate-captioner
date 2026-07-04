import html
import json
import logging
import threading
import time
from pathlib import Path
from typing import Iterator, List

from PIL import Image

from .api import generate_caption

logger = logging.getLogger("ToriiGate.Batch")

# Module-level stop flag. Set by the UI "Stop" button (via request_stop()) and
# polled by run_batch() between images so a batch can be terminated gracefully:
# in-flight requests finish, but no new images are started. Cleared at the
# start of each run so a previous run's stop doesn't leak into the next one.
_stop_event = threading.Event()


def request_stop() -> None:
    """Signal any running batch to stop after the current image(s) finish."""
    _stop_event.set()


# Image extensions we are willing to caption. Lower-cased, compared against
# Path.suffix.lower(). Caption files (.txt/.json) are intentionally excluded
# so re-running a batch never picks up its own previous output.
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}

# Caption types whose output should be persisted as JSON. For these the model
# is asked to emit structured JSON; we save a .json file (best-effort parsed).
JSON_CAPTION_TYPES = {"json", "json_comic", "min_structured_json"}


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
    total: int,
    ok: int,
    skipped: int,
    failed: int,
    elapsed: float,
    done: bool = False,
    error: str = None,
    stopped: bool = False,
) -> str:
    """Render the batch panel as an HTML string: a single-line summary bar
    followed by a bold progress bar. No per-file table (a long batch would
    otherwise force the page to scroll endlessly)."""
    if error:
        return (
            "<div style='font-family:var(--font);color:#e53935;padding:8px;'>"
            f"<b>Batch error:</b> {html.escape(error)}"
            "</div>"
        )

    processed = ok + skipped + failed
    pct = (processed / total * 100.0) if total else 0.0
    if stopped:
        title = "Batch stopped"
    elif done:
        title = "Batch complete"
    else:
        title = "Processing batch"

    bar = (
        "<div style='display:flex;gap:16px;flex-wrap:wrap;padding:6px 0;border-bottom:1px solid #555;margin-bottom:6px;'>"
        f"<b>{html.escape(title)}</b>"
        f"<span>{processed}/{total} processed</span>"
        f"<span style='color:#43a047'>✓ {ok}</span>"
        f"<span style='color:#fb8c00'>⊘ {skipped}</span>"
        f"<span style='color:#e53935'>✗ {failed}</span>"
        f"<span>{elapsed:.1f}s</span>"
        "</div>"
    )

    progress = (
        "<div style='width:100%;height:24px;background:rgba(128,128,128,0.3);"
        "border-radius:6px;overflow:hidden;margin-top:10px;'>"
        f"<div style='width:{pct:.1f}%;height:100%;"
        "background:var(--color-accent,#1f6feb);transition:width .15s;'></div>"
        "</div>"
        f"<div style='font-weight:bold;font-size:large;text-align:center;margin-top:6px;'>"
        f"{pct:.0f}%</div>"
    )
    return bar + progress


def _caption_one(
    path: Path,
    prompt: str,
    server_url: str,
    model_name: str,
    timeout: float,
    max_pixels_mp: float,
    max_new_tokens: int,
    temperature: float,
    caption_type: str,
) -> None:
    """Load *path*, caption it via the API, and save the result next to it.

    Raises on any failure so the caller can record it. Safe to call from
    multiple threads: each call opens its own image and issues its own HTTP
    request, with no shared mutable state.
    """
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


def run_batch(
    folder_path: str,
    overwrite: bool,
    caption_type: str,
    concurrency: int,
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
    saved next to it. *concurrency* controls how many images are captioned in
    parallel (the local llama-server must be able to handle parallel requests,
    e.g. via multiple slots / continuous batching, for this to help).
    Per-image failures are recorded but do not abort the run.

    The run polls the module-level stop flag between images; when the UI "Stop"
    button sets it, in-flight requests are allowed to finish (HTTP requests
    cannot be interrupted mid-flight) but no new images are started, and the
    final progress panel is marked as stopped.
    """
    _stop_event.clear()  # Reset from any previous run.

    try:
        files = collect_images(folder_path)
    except ValueError as exc:
        yield render_batch_html(0, 0, 0, 0, 0.0, done=True, error=str(exc))
        return

    total = len(files)
    ok = skipped = failed = 0
    start = time.perf_counter()

    # Partition up front so a worker is never wasted on an already-captioned
    # file. Skipped files are counted instantly; the bar then fills as the
    # remaining images are processed.
    to_process = []
    for path in files:
        if not overwrite and output_path_for(path, caption_type).exists():
            skipped += 1
        else:
            to_process.append(path)

    yield render_batch_html(total, ok, skipped, failed, time.perf_counter() - start)

    workers = max(1, int(concurrency))
    stopped = False

    if workers == 1:
        for path in to_process:
            if _stop_event.is_set():
                stopped = True
                break
            try:
                _caption_one(
                    path, prompt, server_url, model_name, timeout,
                    max_pixels_mp, max_new_tokens, temperature, caption_type,
                )
                ok += 1
            except Exception:
                logger.exception("[ToriiGate Batch] Failed to caption %s", path)
                failed += 1
            yield render_batch_html(total, ok, skipped, failed, time.perf_counter() - start)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _caption_one, path, prompt, server_url, model_name, timeout,
                    max_pixels_mp, max_new_tokens, temperature, caption_type,
                ): path
                for path in to_process
            }
            for future in as_completed(futures):
                path = futures[future]
                try:
                    future.result()
                    ok += 1
                except Exception:
                    logger.exception("[ToriiGate Batch] Failed to caption %s", path)
                    failed += 1
                yield render_batch_html(total, ok, skipped, failed, time.perf_counter() - start)
                if _stop_event.is_set():
                    stopped = True
                    # Cancel everything not yet started; in-flight ones finish.
                    for f in futures:
                        f.cancel()
                    break

    yield render_batch_html(
        total, ok, skipped, failed, time.perf_counter() - start, done=True, stopped=stopped
    )
