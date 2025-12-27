import requests
from bs4 import BeautifulSoup

url = "https://www.bing.com/search"
params = {"q": "2024年全球AI大模型排名"}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Cookie": "SRCHHPGAVA=CW=1920&CH=1080&DPI=96&TRB=1;"
}

resp = requests.get(url, params=params, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Length: {len(resp.text)}")
soup = BeautifulSoup(resp.text, 'html.parser')
items = soup.select('li.b_algo')
print(f"Items: {len(items)}")
for i, item in enumerate(items[:3]):
    title = item.select_one('h2')
    print(f"{i+1}. {title.get_text() if title else 'No Title'}")
