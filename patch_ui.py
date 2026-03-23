import re

with open("scrapling/ui.py", "r") as f:
    content = f.read()

# Replace the html_content assignment
new_code = """
                        html_content = page.content if page.content else ""
                        if isinstance(html_content, list):
                            html_content = " ".join(str(item) for item in html_content)
                        soup = BeautifulSoup(html_content, 'html.parser')
"""

content = re.sub(
    r'                        html_content = page\.content if page\.content else ""\s+soup = BeautifulSoup\(html_content, \'html\.parser\'\)',
    new_code,
    content
)

# Replace the content_snippet list problem
new_snippet_code = """
                                    snippet = t_page.content if t_page.content else ""
                                    if isinstance(snippet, list):
                                        snippet = " ".join(str(item) for item in snippet)

                                    results.append({
                                        "source_url": crawl_targets[j],
                                        "content_snippet": snippet[:500] + "...",
                                        "status": "success",
                                        "note": f"Internal link crawled for dates {start_date} to {end_date}."
                                    })
"""

content = re.sub(
    r'                                results\.append\({\s+"source_url": crawl_targets\[j\],\s+"content_snippet": t_page\.content\[:500\] \+ "\.\.\." if t_page\.content else "",\s+"status": "success",\s+"note": f"Internal link crawled for dates \{start_date\} to \{end_date\}\."\s+}\)',
    new_snippet_code,
    content
)

with open("scrapling/ui.py", "w") as f:
    f.write(content)
