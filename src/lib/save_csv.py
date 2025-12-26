import pandas as pd


class DataOutPut(object):
    def __init__(self, name):
        self.name = name
        self.result = pd.DataFrame()

    def log(self, m3u8_url, img_url, title):
        df = pd.DataFrame([[m3u8_url, img_url, title]], columns=["影片", "圖片", "標題"])
        self.result = pd.concat([self.result, df])
        self.result.to_csv(f"./{self.name}影片.csv", index=False)