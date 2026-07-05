import base64
import io
import logging
import threading

from PIL import Image

logger = logging.getLogger("ToriiGate.API")

# Shared OpenAI clients keyed by base URL. The sync OpenAI client wraps a single
# httpx.Client with a connection pool that is reused across requests via HTTP
# keep-alive. Sharing one client across batch worker threads — instead of firing
# one-shot requests.post() calls that open and tear down a fresh TCP connection
# per request — keeps the connection alive between calls. This prevents LM
# Studio from treating the connection churn as idle time and repeatedly
# unloading/reloading the model under concurrency, even when VRAM is ample.
# httpx.Client is thread-safe for sync use, so one client per server URL is
# enough for the whole batch (and for single-image requests).
_client_cache = {}
_client_lock = threading.Lock()


def pil_image_to_base64(img_pil: Image.Image, max_pixels_mp: float = 1.0) -> str:
    """Convert a PIL Image to a base64-encoded PNG string suitable for embedding in a data-URI.
    Downscales the image if it exceeds max_pixels_mp to prevent massive TTFT."""
    if img_pil.mode != "RGB":
        img_pil = img_pil.convert("RGB")

    current_pixels = img_pil.width * img_pil.height
    max_pixels_count = max_pixels_mp * 1_000_000
    if current_pixels > max_pixels_count:
        scale = (max_pixels_count / current_pixels) ** 0.5
        new_w = max(1, int(img_pil.width * scale))
        new_h = max(1, int(img_pil.height * scale))
        logger.info(
            f"[ToriiGate API] Downscaling image from {img_pil.width}x{img_pil.height} to {new_w}x{new_h}"
        )
        img_pil = img_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)

    buffered = io.BytesIO()
    img_pil.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def build_vision_payload(
    model_name: str,
    system_prompt: str,
    user_text: str,
    image_b64: str,
    temperature: float,
    max_tokens: int,
    seed: int = 0,
) -> dict:
    """Build an OpenAI-compatible chat-completions payload with an image.

    The returned dict doubles as the kwargs for
    ``client.chat.completions.create()`` — every key (model, messages,
    temperature, max_tokens, and optionally seed) is accepted directly by the
    OpenAI client, so the caller can splat it with ``**payload``.
    """
    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ],
        }
    )

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if seed != 0:
        payload["seed"] = seed
    return payload


def _get_client(server_url: str):
    """Return a shared, connection-pooled OpenAI client for *server_url*.

    The client is created lazily on first use and cached by base URL, so every
    subsequent request — including across batch worker threads — reuses the same
    underlying ``httpx.Client`` connection pool. ``max_retries=0`` surfaces
    errors immediately instead of silently re-issuing the request. ``api_key``
    is arbitrary: llama-server / LM Studio ignore it.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "[ToriiGate API] The 'openai' library is not installed. "
            "Run: pip install openai"
        ) from exc

    base_url = server_url.rstrip("/") + "/v1"
    with _client_lock:
        client = _client_cache.get(base_url)
        if client is None:
            logger.info(f"[ToriiGate API] Creating shared OpenAI client -> {base_url}")
            client = OpenAI(
                base_url=base_url,
                api_key="lm-studio",
                max_retries=0,
            )
            _client_cache[base_url] = client
    return client


def _format_error(exc: Exception, server_url: str) -> str:
    """Translate an OpenAI client exception into a human-readable message.

    Falls back to a generic message if the openai exception types cannot be
    imported (e.g. the library was uninstalled mid-run).
    """
    try:
        from openai import (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
        )
    except ImportError:
        return f"[ToriiGate API] Request failed: {exc}"

    if isinstance(exc, APITimeoutError):
        return (
            "[ToriiGate API] Request timed out. "
            "Try increasing the timeout or reducing max_tokens.\n"
            f"Detail: {exc}"
        )
    if isinstance(exc, APIConnectionError):
        return (
            f"[ToriiGate API] Cannot connect to server at '{server_url}'. "
            "Make sure the server is running and the URL is correct.\n"
            f"Detail: {exc}"
        )
    if isinstance(exc, APIStatusError):
        return (
            f"[ToriiGate API] Server returned HTTP {exc.status_code}.\n"
            f"Response: {exc.response.text}"
        )
    return f"[ToriiGate API] Request failed: {exc}"


def send_chat_request(server_url: str, payload: dict, timeout: float) -> str:
    """Send *payload* through the shared OpenAI client and return the generated
    text. Raises ``RuntimeError`` with a human-readable message on any failure.

    Using the pooled client (instead of a one-shot ``requests.post``) keeps the
    HTTP connection alive between calls, which avoids the model load/unload
    thrash LM Studio exhibits when concurrent requests each open and close a
    fresh connection. Safe to call from multiple threads — they share one client
    and httpx pools connections under the hood.
    """
    client = _get_client(server_url)
    logger.info(
        f"[ToriiGate API] POST via OpenAI client  (model={payload.get('model', '?')})"
    )

    try:
        response = client.chat.completions.create(timeout=timeout, **payload)
    except Exception as exc:
        raise RuntimeError(_format_error(exc, server_url)) from exc

    choices = getattr(response, "choices", None) or []
    if not choices:
        raise RuntimeError(
            "[ToriiGate API] Server returned no choices in the response."
        )

    message = choices[0].message
    return getattr(message, "content", None) or ""


def generate_caption(
    image: Image.Image,
    prompt: str,
    server_url: str = "http://127.0.0.1:8080",
    model_name: str = "DraconicDragon/ToriiGate-0.5-GGUF:Q4_K_M",
    timeout: float = 120.0,
    max_pixels_mp: float = 1.0,
    max_new_tokens: int = 2048,
    temperature: float = 0.5,
    seed: int = 0,
):
    import time

    start_time = time.perf_counter()

    image_b64 = pil_image_to_base64(image, max_pixels_mp)

    payload = build_vision_payload(
        model_name=model_name,
        system_prompt="",
        user_text=prompt,
        image_b64=image_b64,
        temperature=temperature,
        max_tokens=max_new_tokens,
        seed=seed,
    )

    result = send_chat_request(server_url=server_url, payload=payload, timeout=timeout)
    elapsed = time.perf_counter() - start_time
    logger.info(
        f"[ToriiGate] Caption generation finished in {elapsed:.1f}s ({len(result)} chars)."
    )
    return result.strip()
