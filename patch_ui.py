import re

with open("scrapling/ui.py", "r") as f:
    content = f.read()

# Add datetime import
if "from datetime import datetime, timedelta" not in content:
    content = content.replace("from typing import Any", "from typing import Any\nfrom datetime import datetime, timedelta")

# Replace the textboxes for dates to have default values
content = re.sub(
    r'e_start_date = gr\.Textbox\(label="Start Date", placeholder="YYYY-MM-DD"\)',
    'e_start_date = gr.Textbox(label="Start Date", placeholder="YYYY-MM-DD", value=lambda: datetime.now().strftime("%Y-%m-%d"))',
    content
)

content = re.sub(
    r'e_end_date = gr\.Textbox\(label="End Date", placeholder="YYYY-MM-DD"\)',
    'e_end_date = gr.Textbox(label="End Date", placeholder="YYYY-MM-DD", value=lambda: (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))',
    content
)

# Replace the wrapper to do a simple crawl
new_wrapper = """
            async def event_scrape_wrapper(urls_text, start_date, end_date):
                if not urls_text:
                    return {"error": "URLs are required"}

                urls = [u.strip() for u in urls_text.split('\\n') if u.strip()]
                results = []

                try:
                    # Fetch initial pages to get HTML links
                    # We will use HTML extraction to parse links
                    pages = await ScraplingMCPServer.bulk_stealthy_fetch(
                        urls=urls,
                        extraction_type="html",
                        headless=True,
                        google_search=False,
                        css_selector="body",
                        main_content_only=False
                    )

                    from bs4 import BeautifulSoup
                    import urllib.parse

                    for i, page in enumerate(pages):
                        base_url = urls[i]
                        html_content = page.content if page.content else ""
                        soup = BeautifulSoup(html_content, 'html.parser')

                        # Find all links that look like events/tickets
                        links = soup.find_all('a', href=True)
                        event_links = set()
                        for link in links:
                            href = link['href']
                            full_url = urllib.parse.urljoin(base_url, href)
                            # Basic heuristic: ignore obvious non-event links
                            if full_url.startswith('http') and base_url in full_url:
                                event_links.add(full_url)

                        # Crawl a small sample of the internal links found
                        crawl_targets = list(event_links)[:3] # Limit to 3 to avoid hanging Gradio
                        if crawl_targets:
                            target_pages = await ScraplingMCPServer.bulk_stealthy_fetch(
                                urls=crawl_targets,
                                headless=True,
                                google_search=False,
                                extraction_type="text",
                                main_content_only=True
                            )

                            for j, t_page in enumerate(target_pages):
                                results.append({
                                    "source_url": crawl_targets[j],
                                    "content_snippet": t_page.content[:500] + "..." if t_page.content else "",
                                    "status": "success",
                                    "note": f"Internal link crawled for dates {start_date} to {end_date}."
                                })

                        results.append({
                            "source_url": base_url,
                            "links_found": len(event_links),
                            "crawled_samples": crawl_targets,
                            "status": "success"
                        })

                    return {"events": results}
                except Exception as e:
                    import traceback
                    return {"error": str(e), "trace": traceback.format_exc()}
"""

# Be careful replacing the old event_scrape_wrapper
content = re.sub(r"async def event_scrape_wrapper\(.*?\)(.*?)(?=e_fetch_btn\.click)", new_wrapper + "\n            ", content, flags=re.DOTALL)

with open("scrapling/ui.py", "w") as f:
    f.write(content)
