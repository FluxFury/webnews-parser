import os

import requests
from dotenv import load_dotenv

url = "http://localhost:6800/schedule.json"

data = {"project": "webnews_parser",
        "spider": "CSlsMatchesTournamentsSpider",
}

response = requests.post(url, data=data)

if response.status_code == 200:
    print(response.json())
else:
    print(response.json())
