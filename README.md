# ToriiGate Captioner for Stable Diffusion WebUI

_[English](README.md) | [中文](README_zh.md)_

An [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) (and [Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)) for [Minthy/ToriiGate-0.5](https://huggingface.co/Minthy/ToriiGate-0.5), an image captioning model for anime-style and digital art.

Original Model: [Minthy/ToriiGate-0.5](https://huggingface.co/Minthy/ToriiGate-0.5)

GGUF Models: [DraconicDragon/ToriiGate-0.5-GGUF](https://huggingface.co/DraconicDragon/ToriiGate-0.5-GGUF)

> The Q4_K_M quantized GGUF model is recommended, as it is relatively VRAM-friendly.

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

### Recommended: LM Studio

1. Download and install LM Studio: https://lmstudio.ai/
2. Launch LM Studio and enable Developer Mode in the settings.
3. Set LM Studio's model storage directory.
4. Download the GGUF model and the mmproj model and place them in LM Studio's model directory. Note that both models must be in the same subfolder.
   - The model subfolder must be nested inside a folder named after the model author.
   - Taking the GGUF model above as an example, the model path is: `\DraconicDragon\ToriiGate-0.5-GGUF`
5. Rename the mmproj model to `mmproj-BF16.gguf`, otherwise LM Studio cannot detect it.
6. Select the Developer panel on the left, choose model loading at the top, and modify the following parameters (leave the rest at their defaults):
   - Context length: 4096
   - GPU offload: max
   - Try mmap(): off
   - K-cache quantization type: Q8_0
   - V-cache quantization type: Q8_0
7. Load the model, then find the model ID and inference endpoint on the right.
   - Note: This configuration uses roughly 4GB of VRAM. If you don't have enough VRAM, you can reduce the GPU offload layers, trading speed and system memory for VRAM.
8. Find the **ToriiGate Captioner** tab at the top of the WebUI and enter the URL and model ID.

### llama.cpp Inference

1. Start your `llama-server` instance equipped with a vision-capable model (like LLaVA, Qwen-VL, JoyCaption, etc.).
   - For llama.cpp server config, check the guide from original repo: https://github.com/litch230/comfyui_toriigate#running-the-llamacpp-server
2. Launch your SD WebUI.
3. Go to the **ToriiGate Captioner** tab.
4. (Optional) Set the Llama-server URL in the main UI or in the WebUI Settings -> ToriiGate Captioner. The default is `http://127.0.0.1:8080`.
5. Upload an image.
6. Select your preferred **Caption Type**.
7. Enable character lists, descriptions, or global tags if you want the LLM to ground its output to specific details.
8. Click **Generate** and wait for your local LLM to return the caption.

## Configuration

In **Settings -> ToriiGate Captioner**, you can configure:

- **Default Llama-server URL:** The base URL where your LLM API is hosted (e.g., `http://127.0.0.1:8080`).

## Acknowledgements

- **Core Logic & Prompts:** The core captioning prompts, API logic, and grounding mechanisms are adapted and cited from [comfyui_toriigate](https://github.com/litch230/comfyui_toriigate) by litch230. Huge thanks for the foundational work!
