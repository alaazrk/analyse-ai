# test_api.py
from dotenv import load_dotenv
import os, requests, json
load_dotenv()

url = os.getenv("ERPNEXT_URL")
key = os.getenv("ERPNEXT_API_KEY")
sec = os.getenv("ERPNEXT_API_SECRET")

r = requests.get(
    f"{url}/api/resource/Customer",
    params={"fields": json.dumps(["name","customer_name"]), "limit_page_length": 5},
    headers={"Authorization": f"token {key}:{sec}"}
)
print(r.status_code)
print(r.json())