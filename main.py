import argparse
import datetime
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src import tenki

AREA_INFO = json.load(open("src/data/area.json"))


def get_and_save_point_data(outdir):
    filepath = outdir + "obs_point_data.csv"
    if Path(filepath).exists():
        print(f"observation point data already exists. '{filepath}'")
        area_df = pd.read_csv(filepath)
    else:
        start = time.time()
        print("Collecting observation point data...")
        area_df = tenki.get_point_data()
        area_df.to_csv(filepath, index=False)
        t = time.time() - start
        print("Saved observation point data. "
              "Process time: {:.0f}min {:.0f}sec".format(*divmod(t, 60)))

    return area_df


def get_and_save_weather_data(area_df, target_areas, from_, to_, outdir):
    filepath_base = args.outdir + "weather_point{:0>5}_" + f"{from_.date()}_{to_.date()}.csv"

    area_df = area_df[area_df["pref_name"].isin(target_areas)]
    area_df = area_df[area_df["symbol"] == "s"]  # 小さな観測地点は除外

    area_point_arr = area_df[["area_num", "point_num"]].drop_duplicates().values
    expected_time = _calc_expected_process_time(len(area_point_arr), from_, to_)

    start = time.time()
    print("Collecting weather data...\n"
          "It's takes at least {:.0f}min {:.0f}sec".format(*divmod(expected_time, 60)))
    for a, p in area_point_arr:
        filepath = filepath_base.format(p)
        tdf = tenki.get_weather_data(a, p, from_, to_)
        tdf.to_csv(filepath)

    t = time.time() - start
    print("Saved weather data. "
          "Process time: {:.0f}min {:.0f}sec".format(*divmod(t, 60)))


def _calc_expected_process_time(n_point, from_, to_):
    """訪問するページ数 x 1秒"""
    td = datetime.timedelta(days=30)
    n_page_of_date = len(pd.date_range(from_, to_ + td, freq="1M"))
    return n_point * n_page_of_date


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("from_", type=str)
    parser.add_argument("to_", type=str)
    parser.add_argument("--area", nargs="*", choices=list(AREA_INFO.keys()),
                        default=["Tokyo"])
    parser.add_argument("--outdir", type=str, default="data/")
    args = parser.parse_args()

    area_df = get_and_save_point_data(args.outdir)

    target_areas = np.concatenate([AREA_INFO[i] for i in args.area])
    from_ = pd.to_datetime(args.from_)
    to_ = pd.to_datetime(args.to_)
    get_and_save_weather_data(area_df, target_areas, from_, to_, args.outdir)
