import gradio as gr
from typing import List, Tuple
from modules import shared
from .grounding import build_grounding
from .api import generate_caption

CAPTION_TYPES = [
    "short",
    "long_thoughts_v2",
    "long_thoughts",
    "json",
    "long",
    "min_structured_md",
    "json_comic",
    "md_comic",
    "min_structured_json",
    "chroma-style",
]

def on_generate_click(
    image,
    caption_type, use_names, add_tags, tags,
    add_character_list, character_names, character_count,
    add_character_tags, add_character_descriptions,
    char1_name, char1_tags, char1_description,
    char2_name, char2_tags, char2_description,
    char3_name, char3_tags, char3_description,
    char4_name, char4_tags, char4_description,
    char5_name, char5_tags, char5_description,
    server_url, model_name, max_pixels_mp, max_new_tokens, temperature, timeout
):
    if image is None:
        return "Please upload an image first."

    try:
        # 1. Build prompt
        prompt = build_grounding(
            caption_type=caption_type,
            use_names=use_names,
            add_tags=add_tags,
            tags=tags,
            add_character_list=add_character_list,
            character_names=character_names,
            character_count=int(character_count),
            add_character_tags=add_character_tags,
            add_character_descriptions=add_character_descriptions,
            char1_name=char1_name, char1_tags=char1_tags, char1_description=char1_description,
            char2_name=char2_name, char2_tags=char2_tags, char2_description=char2_description,
            char3_name=char3_name, char3_tags=char3_tags, char3_description=char3_description,
            char4_name=char4_name, char4_tags=char4_tags, char4_description=char4_description,
            char5_name=char5_name, char5_tags=char5_tags, char5_description=char5_description,
        )

        # 2. Call API
        actual_url = server_url.strip() if server_url else getattr(shared.opts, "torrigate_server_url", "http://127.0.0.1:8080")
        actual_model = model_name.strip() if model_name else getattr(shared.opts, "torrigate_model_name", "DraconicDragon/ToriiGate-0.5-GGUF:Q4_K_M")

        result = generate_caption(
            image=image,
            prompt=prompt,
            server_url=actual_url,
            model_name=actual_model,
            timeout=float(timeout),
            max_pixels_mp=float(max_pixels_mp),
            max_new_tokens=int(max_new_tokens),
            temperature=float(temperature)
        )

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

def create_ui():
    with gr.Blocks() as torii_interface:
        with gr.Row():
            # Left Column
            with gr.Column(scale=1):
                image_input = gr.Image(label="Source Image", type="pil", height=300, elem_id="torrigate_image_input")

                with gr.Accordion("API Settings", open=False):
                    # We can use shared.opts inside the UI but it only evaluated once. Let's just use it as default if blank.
                    server_url = gr.Textbox(label="Server URL", placeholder="Leave blank to use settings, e.g. http://127.0.0.1:8080", info="Base URL of the llama-server instance.", elem_id="torrigate_server_url")
                    model_name = gr.Textbox(label="Model Name", placeholder="Leave blank to use settings", info="Model identifier string. Must match llama-server router registration.", elem_id="torrigate_model_name")
                    max_pixels_mp = gr.Slider(minimum=0.1, maximum=8.0, step=0.1, value=1.0, label="Max Pixels (MP)", info="Resolution limit sent to the model, in megapixels.", elem_id="torrigate_max_pixels_mp")
                    max_new_tokens = gr.Slider(minimum=64, maximum=8192, step=64, value=512, label="Max New Tokens", info="Maximum generated tokens.", elem_id="torrigate_max_new_tokens")
                    temperature = gr.Slider(minimum=0.0, maximum=2.0, step=0.05, value=0.5, label="Temperature", info="Generation randomness in sample mode.", elem_id="torrigate_temperature")
                    timeout = gr.Slider(minimum=5, maximum=600, step=5, value=120, label="Timeout (s)", info="HTTP request timeout in seconds.", elem_id="torrigate_timeout")

                with gr.Accordion("Grounding Builder", open=True):
                    caption_type = gr.Dropdown(choices=CAPTION_TYPES, value="short", label="Caption Type", info="Caption format. short is fastest; long is detailed natural text; json/min_structured produce structured output.", elem_id="torrigate_caption_type")
                    
                    with gr.Row():
                        use_names = gr.Checkbox(label="Use Names", value=True, info="Try to recognize character names.", elem_id="torrigate_use_names")
                        add_tags = gr.Checkbox(label="Add Tags", value=False, info="Use general tags.", elem_id="torrigate_add_tags")
                        add_character_list = gr.Checkbox(label="Add Char List", value=False, info="Use char list.", elem_id="torrigate_add_character_list")
                        add_character_tags = gr.Checkbox(label="Add Char Tags", value=False, info="Use char tags.", elem_id="torrigate_add_character_tags")
                        add_character_descriptions = gr.Checkbox(label="Add Char Descs", value=False, info="Use char desc.", elem_id="torrigate_add_character_descriptions")
                    
                    tags = gr.Textbox(label="Tags", placeholder="1girl, blue_hair...", lines=2, info="General booru tags for the image, separated by commas. Only added when Add Tags is enabled.", elem_id="torrigate_tags")
                    character_names = gr.Textbox(label="Character Names", placeholder="Name1, Name2...", lines=2, info="General character list, separated by commas. Empty specific chars match to this list by position.", elem_id="torrigate_character_names")
                    character_count = gr.Slider(minimum=1, maximum=5, step=1, value=1, label="Character Count", info="Number of characters to configure.", elem_id="torrigate_character_count")

                    char_inputs = []
                    for i in range(1, 6):
                        with gr.Accordion(f"Character {i}", open=False):
                            c_name = gr.Textbox(label=f"Char {i} Name", info=f"Name/tag for character {i}.", elem_id=f"torrigate_char{i}_name")
                            c_tags = gr.Textbox(label=f"Char {i} Tags", lines=2, info=f"Booru tags specific to character {i}. Uses Char {i} Name, or the #{i} name from Character Names if empty.", elem_id=f"torrigate_char{i}_tags")
                            c_desc = gr.Textbox(label=f"Char {i} Description", lines=2, info=f"Free-form description for character {i}. Useful for personality, uniform, etc.", elem_id=f"torrigate_char{i}_description")
                            char_inputs.extend([c_name, c_tags, c_desc])

            # Right Column
            with gr.Column(scale=1):
                generate_btn = gr.Button("Generate Caption", variant="primary", elem_id="torrigate_generate_btn")
                output_text = gr.Textbox(label="Result", lines=25, interactive=False, elem_id="torrigate_output_text")

        inputs = [
            image_input,
            caption_type, use_names, add_tags, tags,
            add_character_list, character_names, character_count,
            add_character_tags, add_character_descriptions,
        ] + char_inputs + [
            server_url, model_name, max_pixels_mp, max_new_tokens, temperature, timeout
        ]

        generate_btn.click(
            fn=on_generate_click,
            inputs=inputs,
            outputs=output_text
        )

    return [(torii_interface, "ToriiGate Captioner", "torrigate_captioner")]
