import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import re  # 引入正規表達式模組來解析 CSS style
import pandas as pd
# 引入 DrissionPage
from DrissionPage import ChromiumPage, ChromiumOptions


class MissAVScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MissAV 爬蟲 (DrissionPage 修復圖片版)")
        self.root.geometry("750x650")

        # --- 介面佈局 ---
        self.lbl_input = tk.Label(root, text="請輸入番號 (一行一個，例如 IENE-695):", font=("Arial", 12))
        self.lbl_input.pack(pady=5, anchor="w", padx=10)

        self.input_text = scrolledtext.ScrolledText(root, height=8, font=("Arial", 10))
        self.input_text.pack(fill="x", padx=10, pady=5)
        # 預設範例改為您提供的 SSIS-062
        self.input_text.insert(tk.END, "SSIS-062\nIENE-695")

        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=10)

        self.btn_start = tk.Button(self.btn_frame, text="開始爬取", command=self.start_scraping_thread,
                                   bg="#009688", fg="white", font=("Arial", 12, "bold"), padx=20)
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

        thread = threading.Thread(target=self.run_scraper, args=(codes,))
        thread.daemon = True
        thread.start()

    def run_scraper(self, codes):
        page = None
        try:
            self.log("=== 初始化 DrissionPage 瀏覽器 ===")
            co = ChromiumOptions()
            co.set_argument('--no-first-run')
            page = ChromiumPage(addr_or_opts=co)
            self.log("=== 瀏覽器就緒 ===")
            result = pd.DataFrame()
            for i, code in enumerate(codes):
                target_code = code.lower()
                url = f"https://missav.ws/{target_code}"

                self.log(f"正在處理: {target_code} ...")

                try:
                    page.listen.start('m3u8')
                    page.get(url)

                    # Cloudflare 手動驗證檢查
                    title = page.title.lower()
                    if i == 0 or "just a moment" in title or "verify" in title:
                        time.sleep(2)
                        if "just a moment" in page.title.lower():
                            self.log("⚠️ 偵測到 Cloudflare，請手動點擊驗證...")
                            messagebox.showinfo("驗證暫停", "請手動通過 Cloudflare 驗證，\n看到影片頁面後按「確定」。")

                    if "404" in page.title:
                        self.log(f"❌ 失敗 [{target_code}]: 頁面不存在")
                        page.listen.stop()
                        continue

                    self.log("🎧 正在監聽 m3u8 封包...")
                    res = page.listen.wait(timeout=15)  # 稍微延長等待時間

                    # --- 解析標題 ---
                    title = "未知標題"
                    try:
                        ele_h1 = page.ele('tag:h1')
                        if ele_h1: title = ele_h1.text
                    except:
                        pass

                    # --- 解析封面 (更新版) ---
                    img_url = "未知封面"

                    # 方法 1: 嘗試解析 CSS style (針對新版網頁結構)
                    try:
                        # 尋找 class 為 plyr__poster 的 div
                        poster_div = page.ele('.plyr__poster')
                        if poster_div:
                            style_attr = poster_div.attr('style')
                            # 如果 style 屬性存在且包含 url
                            if style_attr and 'url' in style_attr:
                                # 使用 Regex 提取 url('...') 裡面的內容
                                # pattern 解釋: 尋找 url( 開頭，忽略可能的引號，抓取中間非引號的內容，直到遇到右括號
                                match = re.search(r'url\([\'"]?([^\'"]+)[\'"]?\)', style_attr)
                                if match:
                                    img_url = match.group(1)
                                    self.log("(已透過 CSS Style 找到圖片)")
                    except Exception as e:
                        # print(f"CSS style extract failed: {e}")
                        pass

                    # 方法 2: 如果方法 1 失敗，嘗試舊版 video data-poster (備援)
                    if img_url == "未知封面":
                        try:
                            video_ele = page.ele('tag:video')
                            if video_ele and video_ele.attr('data-poster'):
                                img_url = video_ele.attr('data-poster')
                                self.log("(已透過 video tag 找到圖片)")
                        except:
                            pass

                    # 方法 3: 嘗試 meta tag (備援 2)
                    if img_url == "未知封面":
                        try:
                            meta_img = page.ele('tag:meta@property=og:image')
                            if meta_img:
                                img_url = meta_img.attr('content')
                                self.log("(已透過 meta tag 找到圖片)")
                        except:
                            pass

                    # --- 輸出結果 ---
                    if res:
                        m3u8_url = res.url
                        self.log(f"✅ 成功 [{target_code}]:")
                        self.log(f"標題: {title}")
                        self.log(f"封面: {img_url}")
                        self.log(f"影片 (封包): {m3u8_url}")
                        self.log("-" * 40)
                        df = pd.DataFrame([[m3u8_url,img_url,title]],columns=["影片","圖片","標題"])
                        result = pd.concat([result,df])
                        result.to_csv("./影片.csv", index=False)
                    else:
                        self.log(f"❌ 失敗 [{target_code}]: 監聽超時 (未偵測到 m3u8 請求)")

                    page.listen.stop()

                except Exception as e:
                    self.log(f"⚠️ 錯誤 [{target_code}]: {str(e)}")
                    page.listen.stop()

        except Exception as e:
            self.log(f"🔥 啟動失敗: {str(e)}")
        finally:
            self.log("=== 所有任務完成 ===")
            self.root.after(0, lambda: self.btn_start.config(state='normal', text="開始爬取"))


if __name__ == "__main__":
    root = tk.Tk()
    app = MissAVScraperApp(root)
    root.mainloop()