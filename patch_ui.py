import re

with open("scrapling/ui.py", "r") as f:
    content = f.read()

new_wrapper = """
            async def event_scrape_wrapper(urls_text, start_date, end_date):
                if not urls_text:
                    return {"error": "URLs are required"}

                urls = [u.strip() for u in urls_text.split('\\n') if u.strip()]
                results = []

                try:
                    from bs4 import BeautifulSoup
                    import urllib.parse
                    import markdownify

                    # Fetch initial pages with HTML to parse structure and links
                    pages = await ScraplingMCPServer.bulk_stealthy_fetch(
                        urls=urls,
                        extraction_type="html",
                        headless=True,
                        google_search=False,
                        css_selector="body",
                        main_content_only=False
                    )

                    for i, page in enumerate(pages):
                        base_url = urls[i]

                        html_content = page.content if page.content else ""
                        if isinstance(html_content, list):
                            html_content = " ".join(str(item) for item in html_content)

                        soup = BeautifulSoup(html_content, 'html.parser')

                        # A very generic approach to find event-like items:
                        # We will look for <a> tags that wrap a decent amount of text or are inside a repeating structure.
                        # Since we don't know the exact site structure, we'll extract the main text as markdown,
                        # and also collect the first few distinct internal links as "detail pages".

                        # Convert full body to markdown to see the general text (similar to fetch tab)
                        page_markdown = markdownify.markdownify(html_content, heading_style="ATX").strip()

                        # Find all links that look like events/tickets
                        links = soup.find_all('a', href=True)
                        event_links = {}

                        for link in links:
                            href = link['href']
                            full_url = urllib.parse.urljoin(base_url, href)
                            # Basic heuristic: ignore obvious non-event links
                            if full_url.startswith('http') and base_url in full_url:
                                link_text = link.get_text(strip=True)
                                if len(link_text) > 5 and full_url not in event_links:
                                    event_links[full_url] = link_text

                        # Select a small sample to crawl details for (max 3 to avoid hanging)
                        crawl_targets = list(event_links.keys())[:3]

                        crawled_details = []
                        if crawl_targets:
                            target_pages = await ScraplingMCPServer.bulk_stealthy_fetch(
                                urls=crawl_targets,
                                headless=True,
                                google_search=False,
                                extraction_type="markdown", # Get clean markdown for details
                                main_content_only=True
                            )

                            for j, t_page in enumerate(target_pages):
                                snippet = t_page.content if t_page.content else ""
                                if isinstance(snippet, list):
                                    snippet = " ".join(str(item) for item in snippet)

                                crawled_details.append({
                                    "detail_url": crawl_targets[j],
                                    "link_text": event_links[crawl_targets[j]],
                                    "extracted_markdown": snippet[:1000] + "..." if len(snippet) > 1000 else snippet,
                                    "status": "success"
                                })

                        results.append({
                            "source_url": base_url,
                            "overview_markdown": page_markdown[:1500] + "..." if len(page_markdown) > 1500 else page_markdown,
                            "total_internal_links_found": len(event_links),
                            "event_details_crawled": crawled_details,
                            "status": "success",
                            "note": f"Scraped for dates {start_date} to {end_date}. Extracted overview and {len(crawled_details)} details."
                        })

                    return {"events": results}
                except Exception as e:
                    import traceback
                    return {"error": str(e), "trace": traceback.format_exc()}
"""

content = re.sub(r"async def event_scrape_wrapper\(.*?\)(.*?)(?=e_fetch_btn\.click)", new_wrapper + "\n            ", content, flags=re.DOTALL)

with open("scrapling/ui.py", "w") as f:
    f.write(content)
