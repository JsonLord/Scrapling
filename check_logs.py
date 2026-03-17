from huggingface_hub import HfApi
import os
import requests

token = os.environ.get("HF_TOKEN")
api = HfApi(token=token)
repo_id = "harvesthealth/magentic-ui"

try:
    print("Trying to fetch logs via Space info...")
    info = api.space_info(repo_id)
    if hasattr(info, 'runtime'):
         print(f"Hardware: {info.runtime.hardware}")
         print(f"Stage: {info.runtime.stage}")
         print(f"Error Message: {info.runtime.error}")
except Exception as e:
    print(f"Could not get space info: {e}")

# Let's try requests without bearer in case it's a public space
print("Trying public log fetch...")
r = requests.get(f"https://huggingface.co/api/spaces/{repo_id}/logs/build")
print(f"Status: {r.status_code}")
if r.status_code == 200:
    print(r.text[:500])
else:
    print(r.text)
