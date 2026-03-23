with open("scrapling/ui.py", "r") as f:
    content = f.read()

content = content.replace("urls_text.split('\n')", "urls_text.split('\\n')")

with open("scrapling/ui.py", "w") as f:
    f.write(content)
