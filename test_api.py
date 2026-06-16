import requests
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("OSTICKET_URL") + "/api/tickets.json"
headers = {
    "X-API-Key": os.getenv("OSTICKET_API_KEY"),
    "Content-Type": "application/json"
}

r = requests.get(url, headers=headers)
print("Status:", r.status_code)
print("Response:", r.text[:200])
