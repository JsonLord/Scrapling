from huggingface_hub import HfApi
import os

token = os.environ.get("HF_TOKEN")
api = HfApi(token=token)
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
    ]
)
