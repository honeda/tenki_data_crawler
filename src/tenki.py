import time
import datetime
import json
import re
import requests

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

ACCESS_INTERVAL = 1  # sec
URL = "https://www.data.jma.go.jp"

HOKKAIDO = json.load(open("src/data/hokkaido.json"))

DAILY_DATA_COLS = [
    "date",
    "point_num",  # 地域に割り当てられた数値
    "atm_onsite",  # 現地の気圧 [hPa]
    "atm_sea_level",  # 海面の気圧 [mm]
    "precip_total",  # 合計降水量 [mm]
    "precip_max_1h",  # 1時間の最大降水量 [mm]
    "precip_max_10m",  # 10分間の最大降水量 [mm]
    "temp_avg",  # 平均気温 [℃]
    "temp_max",  # 最高気温 [℃]
    "temp_min",  # 最低気温 [℃]
    "hum_avg",  # 平均湿度 [%]
    "hum_min",  # 最低湿度 [%]
    "wind_speed_avg",  # 平均風速 [m/s]
    "wind_speed_max",  # 最大風速 [m/s]
    "dir_wind_speed_max",  # 最大風速の風向き
    "max_instantenious_wind",  # 最大瞬間風速 [ms]
    "dir_max_instantenious_wind",  # 最大瞬間風速の風向き [ms]
    "hour_of_sunshine",  # 日照時間 [hour]
    "snowfall",  # 降雪量 [cm]
    "deepest_snow",  # 最深積雪 [cm]
    "general_cond_daytime",  # 天気概況（06:00 - 18:00）
    "general_cond_nighttime",  # 天気概況（18:00 - 翌06:00）
]

HOURLY_DATA_COLS = [
    "date",
    "point_num",  # 地域に割り当てられた数値
    "atm_onsite",  # 現地の気圧 [hPa]
    "atm_sea_level",  # 海面の気圧 [mm]
    "precip",  # 降水量 [mm]
    "temp",  # 気温 [℃]
    "dew_point_temp",  # 露点温度 [%]
    "vapor_pressure",  # 蒸気圧 [hPa]
    "hum",  # 湿度 [%]
    "wind_speed",  # 風速 [m/s]
    "dir_wind",  # 風向
    "hour_of_sunshine",  # 日照時間 [hour]
    "snowfall",  # 降雪量 [cm]
    "fallen_snow",  # 積雪量 [cm]
    "deepest_snow",  # 最深積雪 [cm]
    "weather_symbol",  # 天気（記号表記）
    "cloud_amt",  # 雲量
    "visibility",  # 視程 [km]
]


class ObservationPoint(dict):
    """地域ごとの情報を格納するクラス"""

    def __init__(self):
        super().__init__()
        self.__dict__ = self

        self.symbol = None  # "s" or "a". 大きい都市だと"s"になる模様
        self.area_num = None  # 地域が属する都道府県に割り当てられた数値
        self.point_num = None  # 地域に割り当てられた数値
        self.point_name = None  # 地域名
        self.point_name_kana = None  # カタカナ地域名
        self.lat = None  # latitude, 緯度
        self.lon = None  # longitude, 経度
        self.elevation = None  # 標高

        # 観測器の有無
        self.obs_precipitation = 0  # 降水量
        self.obs_temperature = 0  # 気温
        self.obs_humidity = 0  # 湿度
        self.obs_wind = 0  # 風, 1の場合と2の場合があるが違いは分からない
        self.obs_sunshine = 0  # 日照時間
        self.obs_snowfall = 0  # 降雪量

        self.obs_from = None  # 観測開始日. 入力されていない場合も多い
        self.name_change_history = {  # 地域名が変わったか
            # prev_name: changed date
        }


def get_point_data(filepath):
    """気象庁の観測地点の情報をまとめたDataFrameを取得する.
    多くのページのスクレイピングを行うので時間がかかる.
    一度DataFrameを作成して保存すれば良いので何度も使う必要はない.

    Args:
        filepath (str): 保存するファイルのパス

    Note:
        --- COLUMNS INFORMATION ---
        symbol: "s" or "a". 大きい都市だと"s"になる模様
        prec_num: 地域が属する都道府県に割り当てられた数値
        point_num: 地域に割り当てられた数値
        point_name: 地域名
        point_name_kana: カタカナ地域名
        lat: latitude, 緯度
        lon: longitude, 経度
        elevation: 標高

        # 観測器の有無
        obs_areaipitation: 降水量
        obs_temperature: 気温
        obs_humidity: 湿度
        obs_wind: 風, 1の場合と2の場合があるが違いは分からない
        obs_sunshine: 日照時間
        obs_snowfall: 降雪量

        obs_from: 観測開始日. 入力されていない場合も多い
        name_change_history: {  # 地域名が変わったか
            # prev_name: changed date
        }
    """
    areas = _get_area_nums()
    time.sleep(ACCESS_INTERVAL)

    points = []
    for n in areas.values():
        points += _get_point_info(n)
        time.sleep(ACCESS_INTERVAL)

    df = pd.DataFrame(points)
    df.fillna(np.nan, inplace=True)  # None to np.nan
    df.replace({}, np.nan, inplace=True)  # {} to np.nan
    df.to_csv("check.csv")
    df["obs_from"] = pd.to_datetime(df["obs_from"])
    # add area name column
    tmp_dic = {v: k for k, v in areas.items()}
    tmp_lst = [tmp_dic[i] for i in df["area_num"]]
    df.insert(1, "area_name", tmp_lst)
    # add prefecture column. (for Hokkaido)
    df.insert(1, "pref_name", [i if i not in HOKKAIDO else "北海道" for i in tmp_lst])

    df.to_csv(filepath, index=False)


def get_weather_data(filepath, area_num, point_num, from_, to_, freq="daily"):
    """観測データを気象庁のHPから取得し、DataFrameで返す.
    取得期間、サンプリングレートによっては時間がかかるので注意.

    Args:
        filepath (str): 保存するファイルのパス
        area_num (int): 地域が属する都道府県に割り当てられた数値
        point_num (int): 地域に割り当てられた数値
        from_ (datetime): 取得開始日
        to_ (datetime): 取得終了日
        freq (str): "daily" or "hourly". defaults to "daily".
    Return:
        DataFrame
    """
    if freq == "daily":
        f = "1M"
        adjusted_to_ = to_ + datetime.timedelta(days=31)
    elif freq == "hourly":
        f = "1D"
        adjusted_to_ = to_ + datetime.timedelta(days=1)
    else:
        raise Exception(f"'freq' must be 'daily' or 'hourly'. passed {freq}")

    url_base = (f"https://www.data.jma.go.jp/obd/stats/etrn/view/{freq}_s1.php?"
                f"prec_no={area_num}&block_no={point_num}" + "&year={}&month={}&day={}&view=")
    df_lst = []
    for d in pd.date_range(from_, adjusted_to_, freq=f):
        url = url_base.format(d.year, d.month, d.day)
        soup = BeautifulSoup(requests.get(url).content, "lxml")
        table = soup.find("table", class_="data2_s")
        if table:
            tdf = pd.read_html(str(table))[0]
            # to datetime
            if freq == "daily":
                tdf.iloc[:, 0] = [
                    datetime.datetime(d.year, d.month, i) for i in tdf.iloc[:, 0]
                ]
            else:
                tdf.iloc[:, 0] = [
                    datetime.datetime(d.year, d.month, d.day, i - 1) for i in tdf.iloc[:, 0]
                ]
            df_lst.append(tdf)
        time.sleep(ACCESS_INTERVAL)

    df = pd.concat(df_lst)
    df.insert(1, "point_num", point_num)
    df = pd.DataFrame(
        df.values,
        columns=DAILY_DATA_COLS if freq == "daily" else HOURLY_DATA_COLS
    )
    df.set_index("date", inplace=True)

    df[from_: to_].to_csv(filepath, index=False)


def _get_area_nums():
    map_url = URL + "/obd/stats/etrn/select/prefecture00.php"
    res = requests.get(map_url)
    soup = BeautifulSoup(res.content, "lxml")

    areas = {}
    ptn = re.compile(r"^.+?prec_no=(\d+?)\&.+?$")
    for i in soup.find_all("area"):
        k = i.get("alt")
        match = ptn.match(i.get("href"))
        if match:
            areas[k] = int(match.group(1))
        else:
            areas[k] = None

    return areas


def _get_point_info(area_num):
    url_base = URL + "/obd/stats/etrn/select/prefecture.php?prec_no={}"
    url = url_base.format(area_num)

    res = requests.get(url)
    soup = BeautifulSoup(res.content, "lxml")

    areas = soup.find_all("area", attrs={"onmouseover": True})
    points = []
    hrefs = []  # 同じ地点の情報が2つあるため"href"で取得済みを検知する
    for a in areas:
        href = a.get("href")
        if href not in hrefs:
            hrefs.append(href)
            points.append(_parse_point_info(a))

    return points


def _parse_point_info(area_tag):
    """地域(point)の'area'タグを渡すとパースしたOvserbationPointクラスのインスタンスを返す.

    Args:
        area_tag (BeautifulSoup): area tag
    Return:
        point
    """
    str_ = area_tag.get("onmouseover")
    g = re.match(r"^javascript:viewPoint\(" + "'(.*?)'," * 22 + "'(.*?)'\);$", str_).groups()

    point = ObservationPoint()
    point.symbol = g[0]
    point.area_num = int(re.match(r"^.+?prec_no=(\d+?)\&.+?$", area_tag.get("href")).group(1))
    point.point_num = int(g[1])
    point.point_name = g[2]
    point.point_name_kana = g[3]
    point.lat = _dms2deg(g[4], g[5])
    point.lon = _dms2deg(g[6], g[7])
    point.elevation = float(g[8])
    point.obs_precipitation = int(g[9])
    point.obs_temperature = int(g[10])
    point.obs_humidity = int(g[11])
    point.obs_wind = int(g[12])
    point.obs_sunshine = int(g[13])
    point.obs_snowfall = int(g[14])

    if g[15] != "9999":  # 初期値の"9999"の場合は情報無し
        point.obs_from = datetime.date(int(g[15]), int(g[16]), int(g[17]))

    # 途中で地域名が変わっている場合の情報をパース
    ptn = re.compile(r"(\d{4})年(\d+?)月(\d+?)日までの地点名「(.+?)」")
    for i in g[18:]:
        match = ptn.match(i)
        if match:
            y, m, d, s = match.groups()
            point.name_change_history[s] = datetime.date(int(y), int(m), int(d))

    return point


def _dms2deg(h, m, s=0):
    """度分秒から度への変換"""
    deg = float(h) + float(m) / 60 + float(s) / 3600
    return deg
