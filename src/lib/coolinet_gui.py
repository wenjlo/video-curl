import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import pandas as pd
# 引入 DrissionPage
from DrissionPage import ChromiumPage, ChromiumOptions


class CoolinetScraperApp:
    def __init__(self, root):
        self.name = "coolinet"
        self.root = root
        self.root.title("Coolinet 爬蟲 (V3 完美全抓版)")
        self.root.geometry("750x650")

        # --- 介面佈局 ---
        self.lbl_input = tk.Label(root, text="請輸入「完整文章網址」 (一行一個):", font=("Arial", 12, "bold"), fg="blue")
        self.lbl_input.pack(pady=5, anchor="w", padx=10)

        self.input_text = scrolledtext.ScrolledText(root, height=8, font=("Arial", 10))
        self.input_text.pack(fill="x", padx=10, pady=5)
        # 預設範例
        self.input_text.insert(tk.END,
                               "https://www.coolinet.net/2025/12/25/%e7%be%8e%e5%b0%bb%e2%99%a1%e7%be%8e%e8%85%b0%e2%99%a1%e5%ae%b3%e7%be%9e%e7%9a%84%e5%a5%b3%e5%ad%a9%e2%99%a1%e8%a3%95%e5%a5%88%e5%90%88%e8%a8%885%e9%ab%94%e4%bd%8d6%e9%80%a3%e7%ba%8c%e6%bf%83%e5%8e%9a/")

        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=10)

        self.btn_start = tk.Button(self.btn_frame, text="開始爬取", command=self.start_scraping_thread,
                                   bg="#FF5722", fg="white", font=("Arial", 12, "bold"), padx=20)
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
                    # 1. 進入文章主頁
                    page.get(url)

                    # --- 抓取標題 ---
                    title = "未知標題"
                    try:
                        ele_h2 = page.ele('css:div.videoWrap h2', timeout=2)
                        if ele_h2:
                            title = ele_h2.text
                        else:
                            ele_h2_backup = page.ele('tag:h2')
                            if ele_h2_backup: title = ele_h2_backup.text
                    except Exception as e:
                        self.log(f"(標題抓取微誤: {str(e)})")

                    # --- 抓取 Iframe 網址 ---
                    player_url = None
                    try:
                        iframe = page.ele('#allmyplayer')
                        if iframe:
                            src = iframe.attr('src')
                            if src.startswith('//'):
                                player_url = 'https:' + src
                            else:
                                player_url = src
                    except:
                        self.log(f"❌ 找不到播放器 Iframe")
                        continue

                    if not player_url:
                        continue

                    self.log(f"標題: {title}")
                    self.log(f"跳轉至播放器頁面...")

                    # 2. 開始監聽並跳轉到播放器頁面
                    page.listen.start('m3u8')
                    page.get(player_url)

                    # --- [新增] 抓取圖片邏輯 ---
                    # 圖片在跳轉後的頁面的 <video> 標籤的 poster 屬性裡
                    img_url = "未知圖片"
                    try:
                        # 根據你的 HTML，這裡使用 css 選擇器抓取 class 為 dplayer-video 的 video 標籤
                        # timeout=5 給它一點時間載入播放器
                        video_ele = page.ele('css:video.dplayer-video', timeout=5)

                        if video_ele:
                            img_url = video_ele.attr('poster')
                        else:
                            # 備援：直接抓 video 標籤
                            video_ele_backup = page.ele('tag:video')
                            if video_ele_backup:
                                img_url = video_ele_backup.attr('poster')

                    except Exception as e:
                        self.log(f"(圖片抓取失敗: {str(e)})")

                    self.log("🎧 正在監聽 m3u8 封包...")
                    res = page.listen.wait(timeout=20)

                    if res:
                        m3u8_url = res.url
                        self.log(f"✅ 成功抓取:")
                        self.log(f"標題: {title}")
                        self.log(f"封面: {img_url}")
                        self.log(f"影片: {m3u8_url}")
                        self.log("-" * 40)
                        df = pd.DataFrame([[m3u8_url,img_url,title]],columns=["影片","圖片","標題"])
                        result = pd.concat([result,df])
                        result.to_csv(f"./{self.name}影片.csv", index=False)
                    else:
                        self.log(f"❌ 監聽超時")

                    page.listen.stop()
                    time.sleep(2)

                except Exception as e:
                    self.log(f"⚠️ 錯誤: {str(e)}")
                    page.listen.stop()

        except Exception as e:
            self.log(f"🔥 啟動失敗: {str(e)}")
        finally:
            self.log("=== 所有任務完成 ===")
            self.root.after(0, lambda: self.btn_start.config(state='normal', text="開始爬取"))


if __name__ == "__main__":
    root = tk.Tk()
    app = CoolinetScraperApp(root)
    root.mainloop()