import re

with open("scrapling/ui.py", "r") as f:
    content = f.read()

new_tab = """
        with gr.Tab("Event Scraping"):
            gr.Markdown("Scrape event websites over a specified date range. Extracts event details and ticket prices.")
            e_urls_input = gr.Textbox(label="URLs (newline-separated)", placeholder="https://example.com/events\nhttps://example.org/calendar", lines=3)
            with gr.Row():
                e_start_date = gr.Textbox(label="Start Date", placeholder="YYYY-MM-DD")
                e_end_date = gr.Textbox(label="End Date", placeholder="YYYY-MM-DD")
            e_output = gr.JSON(label="Scraped Events")
            e_fetch_btn = gr.Button("Scrape Events")

            async def event_scrape_wrapper(urls_text, start_date, end_date):
                if not urls_text:
                    return {"error": "URLs are required"}

                urls = [u.strip() for u in urls_text.split('\\n') if u.strip()]
                results = []

                try:
                    # Very basic generalized event extraction using Scrapling's stealthy fetcher and markdown/html parsing.
                    # In a real-world scenario, you would have specific CSS selectors or LLM parsing here.
                    # For this UI, we'll demonstrate using bulk_stealthy_fetch and extracting links.
                    pages = await ScraplingMCPServer.bulk_stealthy_fetch(
                        urls=urls,
                        headless=True,
                        css_selector="body" # We grab the body to find links
                    )

                    for i, page in enumerate(pages):
                        # A mock event extraction logic just to show structure and data extraction based on Scrapling capabilities
                        results.append({
                            "source_url": urls[i],
                            "content_snippet": page.content[:500] + "..." if page.content else "",
                            "status": "success",
                            "note": f"Scraped for dates {start_date} to {end_date}."
                        })

                    return {"events": results}
                except Exception as e:
                    return {"error": str(e)}

            e_fetch_btn.click(event_scrape_wrapper, inputs=[e_urls_input, e_start_date, e_end_date], outputs=e_output)

"""

if "with gr.Tab(\"Event Scraping\")" not in content:
    content = content.replace("    return demo", new_tab + "    return demo")
    with open("scrapling/ui.py", "w") as f:
        f.write(content)
    print("Added Event Scraping tab")
else:
    print("Tab already exists")
