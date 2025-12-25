import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import re
import time
import pandas as pd
from bs4 import BeautifulSoup

# Selenium 相關模組
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class JableScraperApp:
    def __init__(self, root):
        self.name = "jable"
        self.root = root
        self.root.title("Jable 全能爬蟲器 (標題+封面圖+影片連結)")
        self.root.geometry("750x650")  # 視窗加大一點以容納更多資訊

        # --- 介面佈局 ---
        self.lbl_input = tk.Label(root, text="請輸入番號 (一行一個，例如 mida-441):", font=("Arial", 12))
        self.lbl_input.pack(pady=5, anchor="w", padx=10)

        self.input_text = scrolledtext.ScrolledText(root, height=8, font=("Arial", 10))
        self.input_text.pack(fill="x", padx=10, pady=5)
        self.input_text.insert(tk.END, "mida-441\nssis-150")

        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=10)

        # 背景執行選項
        self.headless_var = tk.BooleanVar(value=True)
        self.chk_headless = tk.Checkbutton(self.btn_frame, text="背景執行 (不顯示視窗)", variable=self.headless_var)
        self.chk_headless.pack(side="left", padx=10)

        self.btn_start = tk.Button(self.btn_frame, text="開始爬取", command=self.start_scraping_thread,
                                   bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), padx=20)
        self.btn_start.pack(side="left", padx=10)

        self.btn_clear = tk.Button(self.btn_frame, text="清除日誌", command=self.clear_log,
                                   font=("Arial", 10))
        self.btn_clear.pack(side="left", padx=10)

        self.lbl_output = tk.Label(root, text="執行結果:", font=("Arial", 12))
        self.lbl_output.pack(pady=5, anchor="w", padx=10)

        self.log_text = scrolledtext.ScrolledText(root, height=18, state='disabled', font=("Microsoft JhengHei", 9))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def start_scraping_thread(self):
        raw_data = self.input_text.get("1.0", tk.END).strip()
        if not raw_data:
            messagebox.showwarning("警告", "請先輸入番號！")
            return

        codes = [line.strip() for line in raw_data.split('\n') if line.strip()]
        self.btn_start.config(state='disabled', text="爬取中...")

        run_headless = self.headless_var.get()

        thread = threading.Thread(target=self.run_scraper, args=(codes, run_headless))
        thread.daemon = True
        thread.start()

    def run_scraper(self, codes, run_headless):
        driver = None
        try:
            self.log("=== 初始化瀏覽器中... ===")

            chrome_options = Options()
            if run_headless:
                chrome_options.add_argument("--headless")

            # 反爬蟲設定
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # 隨機 User-Agent
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            })

            self.log("=== 瀏覽器就緒 ===")
            result = pd.DataFrame()
            for code in codes:
                target_code = code.lower()
                url = f"https://jable.tv/videos/{target_code}/"

                self.log(f"正在處理: {target_code} ...")

                try:
                    driver.get(url)
                    time.sleep(3)  # 等待網頁載入

                    if "403 Forbidden" in driver.title:
                        self.log(f"❌ 失敗 [{target_code}]: 被 403 阻擋")
                        continue

                    # 解析資料
                    page_source = driver.page_source
                    title, m3u8, img_url = self.extract_data(page_source)

                    if m3u8:
                        self.log(f"✅ 成功 [{target_code}]:")
                        self.log(f"標題: {title}")
                        self.log(f"封面: {img_url}")
                        self.log(f"影片: {m3u8}")
                        self.log("-" * 40)
                        df = pd.DataFrame([[m3u8,img_url,title]],columns=["影片","圖片","標題"])
                        result = pd.concat([result,df])
                        result.to_csv(f"./{self.name}影片.csv", index=False)
                    else:
                        self.log(f"❌ 失敗 [{target_code}]: 找不到連結或影片 (可能需登入或影片失效)")

                except Exception as e:
                    self.log(f"⚠️ 錯誤 [{target_code}]: {str(e)}")

        except Exception as e:
            self.log(f"🔥 瀏覽器啟動失敗: {str(e)}")
        finally:
            if driver:
                driver.quit()
            self.log("=== 所有任務完成 ===")
            self.root.after(0, lambda: self.btn_start.config(state='normal', text="開始爬取"))

    @staticmethod
    def extract_data(html_content):
        """
        解析標題、m3u8連結、圖片連結
        回傳: (title, m3u8_url, image_url)
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. 抓取標題
        title = "找不到標題"
        header_div = soup.find('div', class_='header-left')
        if header_div:
            h4_tag = header_div.find('h4')
            if h4_tag:
                title = h4_tag.get_text(strip=True)

        if title == "找不到標題":
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                title = meta_title['content']

        # 2. 抓取圖片 (封面圖)
        image_url = "找不到圖片"
        # 優先嘗試從 video 標籤的 poster 屬性抓
        video_tag = soup.find('video', id='player')
        if video_tag and video_tag.get('poster'):
            image_url = video_tag['poster']
        else:
            # 備用方案：從 meta og:image 抓
            meta_img = soup.find('meta', property='og:image')
            if meta_img:
                image_url = meta_img['content']

        # 3. 抓取 m3u8
        m3u8_url = None
        pattern = r"var hlsUrl = '(.*?)';"

        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and "hlsUrl" in script.string:
                match = re.search(pattern, script.string)
                if match:
                    m3u8_url = match.group(1)
                    break

        return title, m3u8_url, image_url


if __name__ == "__main__":
    root = tk.Tk()
    app = JableScraperApp(root)
    root.mainloop()