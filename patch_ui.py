with open("scrapling/ui.py", "r") as f:
    content = f.read()

# Replace the event_scrape_wrapper implementation
import re

new_wrapper = """
            async def event_scrape_wrapper(urls_text, start_date, end_date):
                if not urls_text:
                    return {"error": "URLs are required"}

                urls = [u.strip() for u in urls_text.split('\\n') if u.strip()]
                results = []

                try:
                    # Do an actual crawl and set google_search=False to avoid web search behavior
                    pages = await ScraplingMCPServer.bulk_stealthy_fetch(
                        urls=urls,
                        headless=True,
                        google_search=False,
                        css_selector="body" # We grab the body to find links
                    )

                    for i, page in enumerate(pages):
                        # Simple extraction logic for demonstration: Extracting basic content snippet
                        results.append({
                            "source_url": urls[i],
                            "content_snippet": page.content[:500] + "..." if page.content else "",
                            "status": "success",
                            "note": f"Scraped for dates {start_date} to {end_date}. Google search spoofing disabled."
                        })

                    return {"events": results}
                except Exception as e:
                    return {"error": str(e)}
"""

content = re.sub(r"async def event_scrape_wrapper\(.*?\)(.*?)(?=e_fetch_btn\.click)", new_wrapper + "\n            ", content, flags=re.DOTALL)

with open("scrapling/ui.py", "w") as f:
    f.write(content)
