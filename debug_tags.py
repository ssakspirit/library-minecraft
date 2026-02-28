"""
페이지 구조 확인 - tags가 왜 안 나오는지
"""
import requests
from bs4 import BeautifulSoup

url = 'https://education.minecraft.net/worlds/code-builder-tutorial'
print(f"URL: {url}")
print()

r = requests.get(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

soup = BeautifulSoup(r.text, 'html.parser')

# H1 확인
h1 = soup.find('h1')
print(f"H1: {h1.get_text(strip=True) if h1 else 'None'}")
print()

# H1 parent 확인
if h1:
    parent = h1.find_parent()
    print(f"Parent element: {parent.name if parent else 'None'}")
    print()

    # UL 찾기
    ul = parent.find('ul')
    print(f"UL found: {bool(ul)}")

    if ul:
        print("LI items:")
        for li in ul.find_all('li'):
            print(f"  - {li.get_text(strip=True)}")
    else:
        print("UL not found in parent")
        print()
        # 다른 방법으로 찾기
        print("All ULs in parent:")
        for i, ul in enumerate(parent.find_all('ul'), 1):
            print(f"  UL #{i}:")
            for li in ul.find_all('li')[:3]:
                print(f"    - {li.get_text(strip=True)}")

# subjects 정보 확인 (원본 데이터에 있음)
print()
print("Checking original data for subjects...")
import json
data = json.load(open('data/resources.json', 'r', encoding='utf-8'))
resource = next((r for r in data if 'code-builder-tutorial' in r['url']), None)
if resource:
    print(f"Subjects from original: {resource.get('subjects', 'None')}")
