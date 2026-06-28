# ToriiGate Captioner (Stable Diffusion WebUI 扩展)

*[English](README.md) | [中文](README_zh.md)*

这是一个适用于 [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)（及 [Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)）的扩展插件，专为使用 [Minthy/ToriiGate-0.5](https://huggingface.co/Minthy/ToriiGate-0.5)（一个用于动漫风格和数字艺术图像反推的模型）而设计。

原始模型：[Minthy/ToriiGate-0.5](https://huggingface.co/Minthy/ToriiGate-0.5)

GGUF 模型：[DraconicDragon/ToriiGate-0.5-GGUF](https://huggingface.co/DraconicDragon/ToriiGate-0.5-GGUF)

## 主要特性

- **连接本地 LLM:** 轻松配置并连接到正在运行的 `llama-server`（例如 `llama.cpp` 提供），在本地使用多模态模型进行图像描述。
- **多种 Caption 格式:** 内置支持多种预设的文本输出类型，包括：
  - `short` (短描述)
  - `long` (长描述)
  - `long_thoughts` / `long_thoughts_v2` (包含思维过程的长描述)
  - `json` / `min_structured_json` / `json_comic` (JSON 格式化输出)
  - `min_structured_md` / `md_comic` (Markdown 格式化输出)
  - `chroma-style`
- **提示词约束 (Grounding):** 
  - 可选择定义全局标签来引导描述的方向。
  - 支持最多定义 5 名角色，可指定其姓名、专属标签和外貌特征描述，从而确保 LLM 生成的内容能准确识别并描述对应角色。
- **参数自定义:** 允许调整生成的 Token 数量上限、温度值 (Temperature)、图像处理分辨率 (百万像素级控制) 以及 API 请求超时时间。

## 安装方法

1. 打开 Stable Diffusion WebUI 界面。
2. 导航到 **Extensions (扩展)** 标签页。
3. 点击 **Install from URL (从网址安装)** 子标签页。
4. 将本仓库的 URL 粘贴到 **URL for extension's git repository** 输入框中。
5. 点击 **Install (安装)**。
6. 切换到 **Installed (已安装)** 子标签页，然后点击 **Apply and restart UI (应用并重启用户界面)**。

*(或者，你可以直接将本仓库克隆到你 WebUI 的 `extensions/` 目录下。)*

## 依赖项

此扩展依赖于 Python 的 `requests` 库。如果你在加载扩展时遇到报错，可以手动执行以下命令安装依赖：
```bash
pip install -r requirements.txt
```

## 使用说明

1. 启动你的 `llama-server` 实例，并加载一个支持视觉的多模态模型（如 LLaVA, Qwen-VL, JoyCaption 等）。
2. 启动 SD WebUI。
3. 切换到 **ToriiGate Captioner** 标签页。
4. （可选）在主界面中，或者进入 WebUI 的 **Settings (设置) -> ToriiGate Captioner** 中修改 Llama-server URL。默认地址为 `http://127.0.0.1:8080`。
5. 上传需要反推提示词的图像。
6. 选择你希望生成的 **Caption Type (输出格式)**。
7. 如果你希望 LLM 在生成描述时聚焦于特定细节，可以启用角色列表、特征描述或全局标签等选项。
8. 点击 **Generate**，等待本地 LLM 返回描述结果。

另外，你也可以使用 LM Studio 等客户端来加载模型。有关 llama.cpp 服务器的配置，请参考原始仓库中的指南：https://github.com/litch230/comfyui_toriigate#running-the-llamacpp-server

## 全局配置

在 WebUI 的 **Settings (设置) -> ToriiGate Captioner** 菜单下，你可以配置：
- **Default Llama-server URL:** LLM API 服务所在的基础 URL（例如：`http://127.0.0.1:8080`）。

## 致谢

- **核心逻辑与提示词:** 本扩展的核心视觉反推提示词、API 交互逻辑以及角色约束定位（Grounding）机制，均移植并参考自 litch230 的 [comfyui_toriigate](https://github.com/litch230/comfyui_toriigate) 项目。非常感谢其提供的优秀基础功能！
