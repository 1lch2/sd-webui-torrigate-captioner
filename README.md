# ToriiGate Captioner for Stable Diffusion WebUI

_[English](README.md) | [中文](README_zh.md)_

An [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) (and [Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)) for [Minthy/ToriiGate-0.5](https://huggingface.co/Minthy/ToriiGate-0.5), an image captioning model for anime-style and digital art.

Original Model: [Minthy/ToriiGate-0.5](https://huggingface.co/Minthy/ToriiGate-0.5)

GGUF Models: [DraconicDragon/ToriiGate-0.5-GGUF](https://huggingface.co/DraconicDragon/ToriiGate-0.5-GGUF)

## Features

- **Connect to Local LLMs:** Configure and connect to a running `llama-server` (e.g., from `llama.cpp`) to run multimodal models for image captioning locally.
- **Multiple Caption Formats:** Supports a wide variety of predefined caption output types:
  - `short`
  - `long`
  - `long_thoughts` / `long_thoughts_v2`
  - `json` / `min_structured_json` / `json_comic`
  - `min_structured_md` / `md_comic`
  - `chroma-style`
- **Prompt Grounding:**
  - Optionally define global tags to guide the captioner.
  - Define up to 5 characters with specific names, tags, and descriptions to ensure accurate and character-aware descriptions.
- **Adjustable Parameters:** Control token count, temperature, image processing size (megapixels), and connection timeouts.

## Installation

1. Open your Stable Diffusion WebUI.
2. Go to the **Extensions** tab.
3. Click on the **Install from URL** sub-tab.
4. Paste the URL of this repository into the **URL for extension's git repository** field.
5. Click **Install**.
6. Go to the **Installed** sub-tab and click **Apply and restart UI**.

_(Alternatively, you can clone this repository directly into your `extensions/` directory.)_

## Requirements

The extension depends on the `requests` library. If you encounter issues, you may manually install it:

```bash
pip install -r requirements.txt
```

## Usage

1. Start your `llama-server` instance equipped with a vision-capable model (like LLaVA, Qwen-VL, JoyCaption, etc.).
2. Launch your SD WebUI.
3. Go to the **ToriiGate Captioner** tab.
4. (Optional) Set the Llama-server URL in the main UI or in the WebUI Settings -> ToriiGate Captioner. The default is `http://127.0.0.1:8080`.
5. Upload an image.
6. Select your preferred **Caption Type**.
7. Enable character lists, descriptions, or global tags if you want the LLM to ground its output to specific details.
8. Click **Generate** and wait for your local LLM to return the caption.

Alternatively, you can use clients like LM Studio to load the model. For llama.cpp server config, check the guide from original repo: https://github.com/litch230/comfyui_toriigate#running-the-llamacpp-server

## Configuration

In **Settings -> ToriiGate Captioner**, you can configure:

- **Default Llama-server URL:** The base URL where your LLM API is hosted (e.g., `http://127.0.0.1:8080`).

## Acknowledgements

- **Core Logic & Prompts:** The core captioning prompts, API logic, and grounding mechanisms are adapted and cited from [comfyui_toriigate](https://github.com/litch230/comfyui_toriigate) by litch230. Huge thanks for the foundational work!
