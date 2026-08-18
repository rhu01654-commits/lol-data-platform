import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv


# 找到项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 加载 .env
load_dotenv(PROJECT_ROOT / ".env")

# 读取 Riot API Key
api_key = os.getenv("RIOT_API_KEY")

if not api_key:
    raise ValueError("没有找到 RIOT_API_KEY，请检查 .env 文件")


# 先调用新加坡服务器的 LOL 状态接口测试连接
url = "https://sg2.api.riotgames.com/lol/status/v4/platform-data"

headers = {
    "X-Riot-Token": api_key
}

try:
    response = requests.get(url, headers=headers, timeout=10)

    print("HTTP Status:", response.status_code)

    if response.status_code == 200:
        print("Riot API connection successful!")
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])

    elif response.status_code == 401:
        print("API Key 无效或已经过期")

    elif response.status_code == 403:
        print("API Key 没有访问权限")

    elif response.status_code == 429:
        print("请求过多，被 Riot 限流")

    else:
        print("Request failed:")
        print(response.text[:500])

except requests.RequestException as e:
    print("Network error:", e)
