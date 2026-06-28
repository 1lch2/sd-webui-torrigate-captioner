import os
from modules import script_callbacks, shared
import gradio as gr

def on_ui_tabs():
    from torrigate.ui import create_ui
    return create_ui()

def on_ui_settings():
    section = ('torrigate', "ToriiGate Captioner")
    
    shared.opts.add_option(
        key='torrigate_server_url',
        info=shared.OptionInfo(
            "http://127.0.0.1:8080",
            label="Default Llama-server URL",
            section=section,
        ),
    )
    
    shared.opts.add_option(
        key='torrigate_model_name',
        info=shared.OptionInfo(
            "DraconicDragon/ToriiGate-0.5-GGUF:Q4_K_M",
            label="Default Model Name",
            section=section,
        ),
    )

script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
