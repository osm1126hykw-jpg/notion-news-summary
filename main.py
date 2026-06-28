import os
import time
import requests
from bs4 import BeautifulSoup
from google import genai

# 環境変数の取得
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# APIの初期化
client = genai.Client(api_key=GEMINI_API_KEY)

def get_url_from_notion():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    # 「URL」があり、かつ「要約」が空欄のページを検索
    payload = {
        "filter": {
            "and": [
                {
                    "property": "URL",
                    "url": {
                        "is_not_empty": True
                    }
                },
                {
                    "property": "要約",
                    "rich_text": {
                        "is_empty": True
                    }
                }
            ]
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        print("Notionからのデータ取得に失敗しました:", response.text)
        return []

def update_notion_summary(page_id, summary_text):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "properties": {
            "要約": {
                "rich_text": [
                    {
                        "text": {
                            "content": summary_text
                        }
                    }
                ]
            }
        }
    }
    response = requests.patch(url, json=payload, headers=headers)
    return response.status_code == 200

def get_web_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        text = " ".join([p.text for p in soup.find_all('p')])
        return text[:3000]
    except Exception as e:
        print(f"URLの取得に失敗しました ({url}): {e}")
        return None

def summarize_with_gemini(text):
    try:
        prompt = f"以下のウェブページの内容を、日本語で3行程度の分かりやすい箇条書きで要約してください。\n\n{text}"
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"Geminiでの要約に失敗しました: {e}")
        return None

def main():
    pages = get_url_from_notion()
    if not pages:
        print("要約が空欄のページが見つかりませんでした。")
        return

    for page in pages:
        page_id = page["id"]
        properties = page["properties"]
        
        url = properties.get("URL", {}).get("url")
        if not url:
            continue
            
        print(f"処理中: {url}")
        
        web_text = get_web_content(url)
        if not web_text:
            continue
            
        summary = summarize_with_gemini(web_text)
        if not summary:
            continue
            
        if update_notion_summary(page_id, summary):
            print("Notionへの要約書き込みが成功しました！")
        else:
            print("Notionへの書き込みに失敗しました。")

if __name__ == "__main__":
    main()
