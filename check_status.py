from huggingface_hub import HfApi
import os
import time

api = HfApi(token=os.environ.get("HF_TOKEN"))
repo_id = "harvesthealth/magentic-ui"

print(f"Monitoring space {repo_id}...")
for _ in range(30):
    try:
        space = api.space_info(repo_id)
        status = space.runtime.stage
        print(f"Status: {status}")
        if status in ["RUNNING", "RUNNING_BUILDING"]:
            print("Space is running!")
            break
        elif status == "BUILDING":
            print("Space is building...")
        elif status == "ERROR":
            print("Space failed to build/run!")
            break
        else:
            print(f"Space is in state: {status}")
    except Exception as e:
        print(f"Error checking status: {e}")
        break
    time.sleep(10)
