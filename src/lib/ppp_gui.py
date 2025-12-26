import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import re
import pandas as pd
# 引入 DrissionPage
from DrissionPage import ChromiumPage, ChromiumOptions
from save_csv import DataOutPut

class PPPScraperApp:
    def __init__(self, root):
        self.name = "ppp"
        self.data = DataOutPut(self.name)
        self.root = root
        self.root.title("PPP.Porn 爬蟲 (DrissionPage 秒抓版)")
        self.root.geometry("750x650")

        # --- 介面佈局 ---
        self.lbl_input = tk.Label(root, text="請輸入「影片頁面網址」 (一行一個):", font=("Arial", 12, "bold"), fg="blue")
        self.lbl_input.pack(pady=5, anchor="w", padx=10)

        self.input_text = scrolledtext.ScrolledText(root, height=8, font=("Arial", 10))
        self.input_text.pack(fill="x", padx=10, pady=5)
        # 預設範例
        self.input_text.insert(tk.END, "https://ppp.porn/v/inpq5b/")

        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=10)

        self.btn_start = tk.Button(self.btn_frame, text="開始爬取", command=self.start_scraping_thread,
                                   bg="#E91E63", fg="white", font=("Arial", 12, "bold"), padx=20)
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
            messagebox.showwarning("警告", "請先輸入網址！")
            return

        urls = [line.strip() for line in raw_data.split('\n') if line.strip()]
        self.btn_start.config(state='disabled', text="爬取中...")

        thread = threading.Thread(target=self.run_scraper, args=(urls,))
        thread.daemon = True
        thread.start()

    def run_scraper(self, urls):
        page = None
        try:
            self.log("=== 初始化瀏覽器 ===")
            co = ChromiumOptions()
            co.set_argument('--no-first-run')
            co.set_argument('--mute-audio')

            page = ChromiumPage(addr_or_opts=co)
            self.log("=== 瀏覽器就緒 ===")
            result = pd.DataFrame()
            for i, url in enumerate(urls):
                self.log(f"正在處理第 {i + 1} 個網址...")

                try:
                    page.get(url)

                    # 等待一下確保網頁載入
                    time.sleep(2)

                    # 1. 抓取標題
                    # 對應 HTML: <h2 class="content-details__title">...</h2>
                    title = "未知標題"
                    try:
                        ele_h2 = page.ele('.content-details__title')
                        if ele_h2: title = ele_h2.text
                    except:
                        pass

                    # 2. 抓取 M3U8 (使用 Regex 從原始碼抓取)
                    # 對應 HTML: var stream = 'https://...';
                    m3u8_url = None
                    try:
                        html_content = page.html
                        # Regex 解釋: 尋找 var stream = '單引號內的內容'
                        pattern = r"var\s+stream\s*=\s*'([^']+)'"
                        match = re.search(pattern, html_content)
                        if match:
                            m3u8_url = match.group(1)
                    except Exception as e:
                        self.log(f"Regex 解析失敗: {e}")

                    # 3. 抓取圖片
                    # 對應 HTML: <video ... poster="...">
                    img_url = "未知圖片"
                    try:
                        video_ele = page.ele('tag:video')
                        if video_ele:
                            img_url = video_ele.attr('poster')

                        # 如果 video 標籤沒有，嘗試找 plyr__poster
                        if not img_url:
                            poster_div = page.ele('.plyr__poster')
                            if poster_div:
                                style = poster_div.attr('style')
                                match = re.search(r"url\(['\"]?([^'\"]+)['\"]?\)", style)
                                if match: img_url = match.group(1)
                    except:
                        pass

                    # 輸出結果
                    if m3u8_url:
                        self.log(f"✅ 成功抓取:")
                        self.log(f"標題: {title}")
                        self.log(f"封面: {img_url}")
                        self.log(f"影片: {m3u8_url}")
                        self.log("-" * 40)
                        self.data.log(m3u8_url, img_url,title)
                        # df = pd.DataFrame([[m3u8_url,img_url,title]],columns=["影片","圖片","標題"])
                        # result = pd.concat([result,df])
                        # result.to_csv(f"./{self.name}影片.csv", index=False)
                    else:
                        self.log(f"❌ 失敗: 在原始碼中找不到 var stream 變數")

                except Exception as e:
                    self.log(f"⚠️ 錯誤: {str(e)}")

        except Exception as e:
            self.log(f"🔥 啟動失敗: {str(e)}")
        finally:
            self.log("=== 所有任務完成 ===")
            self.root.after(0, lambda: self.btn_start.config(state='normal', text="開始爬取"))


if __name__ == "__main__":
    root = tk.Tk()
    app = PPPScraperApp(root)
    root.mainloop()