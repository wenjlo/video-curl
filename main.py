from src.lib.jable_gui import JableScraperApp
from src.lib.missav_gui import MissAVScraperApp
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = MissAVScraperApp(root)
    root.mainloop()