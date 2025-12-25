import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import json
import re

# 引入 DrissionPage
from DrissionPage import ChromiumPage, ChromiumOptions


class KanavUnlockerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Maccms/Cloudflare 連結解鎖器")
        self.root.geometry("850x700")

        # --- 介面佈局 ---
        self.lbl_input = tk.Label(root, text="請輸入「原始播放頁面網址」 (一行一個):", font=("Arial", 12, "bold"),
                                  fg="blue")
        self.lbl_input.pack(pady=5, anchor="w", padx=10)

        self.input_text = scrolledtext.ScrolledText(root, height=5, font=("Arial", 10))
        self.input_text.pack(fill="x", padx=10, pady=5)
        # 你的範例網址
        self.input_text.insert(tk.END, "https://kanav.ad/index.php/vod/play/id/97927/sid/1/nid/1.html")

        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=10)

        self.btn_start = tk.Button(self.btn_frame, text="開始提取", command=self.start_scraping_thread,
                                   bg="#D32F2F", fg="white", font=("Arial", 12, "bold"), padx=20)
        self.btn_start.pack(side="left", padx=10)

        self.btn_clear = tk.Button(self.btn_frame, text="清除日誌", command=self.clear_log,
                                   font=("Arial", 10))
        self.btn_clear.pack(side="left", padx=10)

        self.lbl_output = tk.Label(root, text="提取結果 (含 PotPlayer 格式):", font=("Arial", 12))
        self.lbl_output.pack(pady=5, anchor="w", padx=10)

        self.log_text = scrolledtext.ScrolledText(root, height=25, state='disabled', font=("Consolas", 10),
                                                  bg="#1e1e1e", fg="#00ff00")
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
        self.btn_start.config(state='disabled', text="提取中...")

        thread = threading.Thread(target=self.run_scraper, args=(urls,))
        thread.daemon = True
        thread.start()

    def run_scraper(self, urls):
        try:
            self.log("=== 初始化瀏覽器 ===")
            co = ChromiumOptions()
            co.set_argument('--no-first-run')
            co.set_argument('--mute-audio')

            page = ChromiumPage(addr_or_opts=co)
            self.log("=== 瀏覽器就緒 ===")

            for i, url in enumerate(urls):
                self.log(f"正在處理: {url} ...")

                try:
                    # 1. 開始監聽封包
                    page.listen.start('m3u8')
                    page.get(url)

                    # 2. 抓取標題 (從 Maccms 變數)
                    title = "未知標題"
                    try:
                        html = page.html
                        match = re.search(r'player_aaaa\s*=\s*(\{.*?\})', html)
                        if match:
                            data = json.loads(match.group(1))
                            if 'vod_data' in data:
                                title = data['vod_data']['vod_name']
                        else:
                            ele = page.ele('tag:h1')
                            if ele: title = ele.text
                    except:
                        pass

                    self.log(f"標題: {title}")
                    self.log("🎧 等待 m3u8 請求 (獲取 Headers)...")

                    # 嘗試點擊 iframe 確保觸發請求
                    try:
                        iframe = page.ele('tag:iframe')
                        if iframe: iframe.click()
                    except:
                        pass

                    # 等待封包
                    res = page.listen.wait(timeout=20)

                    if res:
                        m3u8_url = res.url
                        headers = res.request.headers

                        # === 關鍵：提取 Referer 和 User-Agent ===
                        referer = headers.get('Referer', '')
                        user_agent = headers.get('User-Agent', '')

                        self.log("-" * 40)
                        self.log(f"✅ 破解成功！")
                        self.log(f"🎬 片名: {title}")
                        self.log("-" * 40)

                        self.log("🔗 原始 M3U8 連結 (直接開會被擋):")
                        self.log(m3u8_url)
                        self.log("\n🛡️ 必備 Referer (來源偽裝):")
                        self.log(referer)

                        self.log("\n🚀 【PotPlayer 播放方法】 (複製整行):")
                        # PotPlayer 支援在網址後加 |Referer=... 來偽裝
                        potplayer_link = f"{m3u8_url}|Referer={referer}&User-Agent={user_agent}"
                        self.log(potplayer_link)

                        self.log("\n📝 【FFmpeg/N_m3u8DL-RE 下載參數】:")
                        ffmpeg_args = f'-headers "Referer: {referer}" -user_agent "{user_agent}"'
                        self.log(ffmpeg_args)
                        self.log("-" * 40)

                    else:
                        self.log(f"❌ 監聽超時 (未抓到連結)")

                    page.listen.stop()

                except Exception as e:
                    self.log(f"⚠️ 錯誤: {str(e)}")
                    page.listen.stop()

        except Exception as e:
            self.log(f"🔥 啟動失敗: {str(e)}")
        finally:
            self.log("=== 所有任務結束 ===")
            self.root.after(0, lambda: self.btn_start.config(state='normal', text="開始提取"))


if __name__ == "__main__":
    root = tk.Tk()
    app = KanavUnlockerApp(root)
    root.mainloop()