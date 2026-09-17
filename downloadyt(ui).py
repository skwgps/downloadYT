import os
import sys
import threading
import subprocess
import customtkinter as ctk
from PIL import Image
from pytubefix import YouTube

# 設定介面風格 (Dark/Light, blue/green)
ctk.set_appearance_mode("System")  # 跟隨系統主題
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube 影片下載")
        self.geometry("520x460")
        self.resizable(False, False)

        # ---------------- 學校 Logo 設定 ----------------
        # ---------------- 學校 Logo 動態路徑設定 ----------------
        # 1. 取得此 Python 檔所在的真實資料夾路徑 (例如: C:\Users\andy\Desktop\VSC\DownloadYT)
        if getattr(sys, 'frozen', False):
            # 當使用 PyInstaller 打包成 .exe 時使用的暫存目錄
            BASE_DIR = sys._MEIPASS
        else:
            # 正常執行 .py 檔時的目錄
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        logo_path = os.path.join(BASE_DIR, "school_logo.png")
        
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            # 自動調整 Logo 尺寸 (寬度 120px, 高度按比例縮放)
            aspect_ratio = img.height / img.width
            logo_image = ctk.CTkImage(light_image=img, dark_image=img, size=(120, int(120 * aspect_ratio)))
            
            self.logo_label = ctk.CTkLabel(self, image=logo_image, text="")
            self.logo_label.pack(pady=(15, 5))
        else:
            # 若無 Logo 圖片，顯示文字佔位
            self.logo_label = ctk.CTkLabel(self, text="[ 請放入 school_logo.png ]", font=("微軟正黑體", 12), text_color="gray")
            self.logo_label.pack(pady=(15, 5))

        # ---------------- 介面元件 ----------------
        # 標題
        self.lbl_title = ctk.CTkLabel(self, text="高畫質影片下載工具", font=("微軟正黑體", 20, "bold"))
        self.lbl_title.pack(pady=(5, 15))

        # 網址輸入框
        self.entry_url = ctk.CTkEntry(self, placeholder_text="請貼上 YouTube 影片網址...", width=420, height=35)
        self.entry_url.pack(pady=10)

        # 解析度選擇下拉選單
        self.res_option = ctk.CTkOptionMenu(
            self, 
            values=["1080p (最佳畫質)", "720p (標準畫質)", "480p (低畫質)", "僅下載純音訊 (MP3)"],
            width=200
        )
        self.res_option.set("1080p (最佳畫質)")
        self.res_option.pack(pady=10)

        # 下載按鈕
        self.btn_download = ctk.CTkButton(
            self, 
            text="開始下載", 
            font=("微軟正黑體", 14, "bold"),
            height=38,
            command=self.start_download_thread
        )
        self.btn_download.pack(pady=15)

        # 狀態顯示文字
        self.lbl_status = ctk.CTkLabel(self, text="狀態：準備就緒", font=("微軟正黑體", 13), text_color="gray")
        self.lbl_status.pack(pady=10)

    # ---------------- 下載邏輯與多執行緒 ----------------
    def start_download_thread(self):
        url = self.entry_url.get().strip()
        if not url:
            self.lbl_status.configure(text="錯誤：請輸入有效的 YouTube 網址！", text_color="red")
            return

        self.btn_download.configure(state="disabled")
        self.lbl_status.configure(text="狀態：正在讀取影片資訊...", text_color="#E67E22")

        # 啟用新執行緒處理下載，防止 UI 凍結卡死
        threading.Thread(target=self.download_process, args=(url,), daemon=True).start()

    def download_process(self, url):
        try:
            # 優先使用 WEB 用戶端繞過限制
            try:
                yt = YouTube(url, client='WEB')
            except Exception:
                yt = YouTube(url, client='ANDROID')

            selected_option = self.res_option.get()

            # 純音訊下載
            if "純音訊" in selected_option:
                self.lbl_status.configure(text="狀態：正在下載音訊檔...", text_color="#E67E22")
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                out_file = audio_stream.download()
                base, ext = os.path.splitext(out_file)
                os.rename(out_file, base + '.mp3')

            # 影片下載與合併
            else:
                res_map = {
                    "1080p (最佳畫質)": "1080p",
                    "720p (標準畫質)": "720p",
                    "480p (低畫質)": "480p"
                }
                target_res = res_map.get(selected_option, "1080p")

                self.lbl_status.configure(text=f"狀態：正在下載 {target_res} 影片與音訊...", text_color="#E67E22")

                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                video_streams = yt.streams.filter(adaptive=True, only_video=True, res=target_res)

                if not video_streams:
                    video_stream = yt.streams.filter(adaptive=True, only_video=True).order_by('resolution').desc().first()
                else:
                    video_stream = video_streams.order_by('fps').desc().first()

                audio_path = audio_stream.download(filename_prefix="aud_temp_")
                video_path = video_stream.download(filename_prefix="vid_temp_")

                self.lbl_status.configure(text="狀態：正在使用 FFmpeg 合併高畫質檔案...", text_color="#E67E22")

                clean_title = "".join(c for c in yt.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
                output_filename = f"{clean_title}.mp4"

                cmd = f'ffmpeg -y -i "{video_path}" -i "{audio_path}" -c:v copy -c:a aac "{output_filename}"'
                subprocess.run(cmd, shell=True)

                if os.path.exists(audio_path): os.remove(audio_path)
                if os.path.exists(video_path): os.remove(video_path)

            self.lbl_status.configure(text="狀態：下載完成！", text_color="#2ECC71")

        except Exception as e:
            self.lbl_status.configure(text=f"下載失敗：{str(e)[:30]}...", text_color="red")

        finally:
            self.btn_download.configure(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()