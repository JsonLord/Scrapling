from huggingface_hub import HfApi
import os

token = os.environ.get("HF_TOKEN")
api = HfApi(token=token)

print("Uploading updated Space configuration...")
api.upload_folder(
    folder_path=".",
    repo_id="harvesthealth/magentic-ui",
    repo_type="space",
    ignore_patterns=[
        ".git/*",
        ".github/*",
        "docs/*",
        "images/*",
        "tests/*",
        "venv/*",
        ".pytest_cache/*",
        "__pycache__/*",
        "*.sqlite3",
        "*.db",
        ".env",
        "deploy.py"
    ],
    commit_message="fix: resolve SyntaxError indentation from Gradio Hub logging"
)
