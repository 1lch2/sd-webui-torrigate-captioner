import base64
import io
import json
import logging
from PIL import Image

logger = logging.getLogger("ToriiGate.API")

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
        logger.info(f"[ToriiGate API] Downscaling image from {img_pil.width}x{img_pil.height} to {new_w}x{new_h}")
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
    """Build an OpenAI-compatible chat-completions payload with an image."""
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

def send_chat_request(server_url: str, payload: dict, timeout: float) -> str:
    """POST *payload* to `{server_url}/v1/chat/completions` and return the
    generated text. Raises a `RuntimeError` with a human-readable message
    on any failure."""
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "[ToriiGate API] The 'requests' library is not installed. "
            "Run: pip install requests"
        ) from exc

    endpoint = server_url.rstrip("/") + "/v1/chat/completions"
    logger.info(f"[ToriiGate API] POST -> {endpoint}  (model={payload.get('model', '?')})")

    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            f"[ToriiGate API] Cannot connect to llama-server at '{server_url}'. "
            "Make sure llama-server is running and the URL is correct.\n"
            f"Detail: {exc}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            f"[ToriiGate API] Request timed out after {timeout}s. "
            "Try increasing the timeout or reducing max_tokens.\n"
            f"Detail: {exc}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"[ToriiGate API] HTTP error: {exc}") from exc

    if not response.ok:
        try:
            error_body = response.json()
        except Exception:
            error_body = response.text
        raise RuntimeError(
            f"[ToriiGate API] Server returned HTTP {response.status_code}.\n"
            f"Response: {json.dumps(error_body, ensure_ascii=False, indent=2)}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"[ToriiGate API] Server returned invalid JSON. "
            f"Response:\n{response.text}"
        ) from exc

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(
            f"[ToriiGate API] Server returned no choices. "
            f"Response:\n{json.dumps(data, indent=2)}"
        )

    return choices[0].get("message", {}).get("content", "")

def generate_caption(
    image: Image.Image,
    prompt: str,
    server_url: str = "http://127.0.0.1:8080",
    model_name: str = "DraconicDragon/ToriiGate-0.5-GGUF:Q4_K_M",
    timeout: float = 120.0,
    max_pixels_mp: float = 1.0,
    max_new_tokens: int = 512,
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
    logger.info(f"[ToriiGate] Caption generation finished in {elapsed:.1f}s ({len(result)} chars).")
    return result.strip()
