import gradio as gr
from scrapling.core.ai import ScraplingMCPServer
import asyncio
from typing import Any

def create_ui():
    with gr.Blocks(title="Scrapling") as demo:
        gr.Markdown("# Scrapling Web Interface")

        with gr.Tab("Fetch (HTTP)"):
            gr.Markdown("Standard HTTP Fetcher. Fast but less stealthy.")
            url_input = gr.Textbox(label="URL", placeholder="https://example.com")
            selector_input = gr.Textbox(label="CSS Selector (Optional)", placeholder=".content")
            output = gr.JSON(label="Result")
            fetch_btn = gr.Button("Fetch")

            async def fetch_wrapper(url, selector):
                if not url:
                    return {"error": "URL is required"}
                try:
                    # ScraplingMCPServer.get is synchronous or async?
                    # In code: staticmethod def get(...) -> ResponseModel:
                    # It calls Fetcher.get which is synchronous.
                    # Gradio handles async/sync. But running sync function in async context might block.
                    # Since it is blocking, we should probably run it in executor or just let Gradio handle it.
                    # But ScraplingMCPServer.get uses 'impersonate' which uses curl_cffi.
                    result = ScraplingMCPServer.get(url, css_selector=selector if selector else None)
                    return result.model_dump()
                except Exception as e:
                    return {"error": str(e)}

            fetch_btn.click(fetch_wrapper, inputs=[url_input, selector_input], outputs=output)

        with gr.Tab("Stealthy Fetch (Browser)"):
            gr.Markdown("Stealthy Browser Fetcher (Playwright). Slower but bypasses bot protection.")
            s_url_input = gr.Textbox(label="URL")
            s_selector_input = gr.Textbox(label="CSS Selector (Optional)")
            s_headless = gr.Checkbox(label="Headless", value=True)
            s_output = gr.JSON(label="Result")
            s_fetch_btn = gr.Button("Stealthy Fetch")

            async def stealthy_fetch_wrapper(url, selector, headless):
                if not url:
                    return {"error": "URL is required"}
                try:
                    result = await ScraplingMCPServer.stealthy_fetch(
                        url,
                        css_selector=selector if selector else None,
                        headless=headless
                    )
                    return result.model_dump()
                except Exception as e:
                    return {"error": str(e)}

            s_fetch_btn.click(stealthy_fetch_wrapper, inputs=[s_url_input, s_selector_input, s_headless], outputs=s_output)

    return demo
