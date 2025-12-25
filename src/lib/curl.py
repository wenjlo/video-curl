import requests
import cloudscraper
from bs4 import BeautifulSoup
import re



class JableCurl:
    def __init__(self):
        self.url = 'https://jable.tv/videos'
    @staticmethod
    def get_html_with_cloudscraper(target_url):
        scraper = cloudscraper.create_scraper()  # 建立一個能處理 Cloudflare 的 session
        try:
            response = scraper.get(target_url)
            if response.status_code == 200:
                print("CloudScraper 請求成功！")
                return response.text
            else:
                print(f"CloudScraper 請求失敗，狀態碼: {response.status_code}")
                return None
        except Exception as e:
            print(f"發生錯誤: {e}")
            return None

    # --- 方法 2: 使用普通 Requests (加上 User-Agent) ---
    # 注意：這在 Jable 上很高機率會失敗 (403 Forbidden)
    @staticmethod
    def get_html_with_requests(target_url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            response = requests.get(target_url, headers=headers)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Requests 請求失敗，狀態碼: {response.status_code} (可能是被 Cloudflare 擋住了)")
                return None
        except Exception as e:
            print(f"發生錯誤: {e}")
            return None
    def curl(self, code):
        url = f"{self.url}/{code}/"
        print(url)
        html_content = self.get_html_with_cloudscraper(url)

        # 如果 CloudScraper 沒裝，才試試看普通 requests (通常不建議)
        if not html_content:
            print("嘗試使用普通 Requests...")
            html_content = self.get_html_with_requests(url)

        if html_content:
            # 解析 HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # 尋找隱藏在 script 中的 m3u8 網址
            scripts = soup.find_all('script')
            found_m3u8 = False

            for script in scripts:
                if script.string and "hlsUrl" in script.string:
                    # 使用 Regex 提取網址
                    pattern = r"var hlsUrl = '(.*?)';"
                    match = re.search(pattern, script.string)
                    if match:
                        m3u8_url = match.group(1)
                        print("-" * 30)
                        print("成功抓取 m3u8 網址：")
                        print(m3u8_url)
                        print("-" * 30)
                        found_m3u8 = True
                        break

            if not found_m3u8:
                print("已取得 HTML，但在 Script 中找不到 m3u8 連結。")