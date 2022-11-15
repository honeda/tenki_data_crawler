# 天気データ収集プログラム

気象庁のサイト（https://www.jma.go.jp/jma/index.html ）から過去の天気データを収集するプログラムです。

* 取得するのは日ごとの天気データです。
* 都道府県や地域（関東、近畿など）を指定してデータを取得できます。
* 取得したデータはcsv形式で保存されます。

## 注意
* 天気データの収集はスクレイピングで行います。2022年11月現在のrobots.txtや利用規約には遵守していると認識していますが、プログラムを使用する場合は自身で確認してください。

  * [気象庁HP robots.txt](https://www.jma.go.jp/robots.txt)
  * [気象庁HP 利用規約](https://www.jma.go.jp/jma/kishou/info/coment.html)

<br>

* このプログラムはサイトへのアクセス頻度を1回/1秒になるようにしていますが、同時に複数のプロセスで動かす場合などは大量にアクセスしてしまう可能性があるので注意してください。

* 対象のデータが膨大であるため、このプログラムで全観測地点、全期間のデータが問題なく取得できることは確認できていません。  
  エラーが発生する、もしくはエラーが起きないもののデータに不具合が生じる可能性があります。

<br>

## 使い方

```
.
├── README.md
├── data
├── main.py
├── requirements.txt
├── .python-version
└── src
    ├── data
    └── tenki.py
```

<br>

上記ディレクトリ構成の"`.`"にいる状態で下記を実行すると、2022年1月1日～2022年1月31日までの東京都内の観測地点のデータを取得し、"`./data`"にcsvファイルを保存します。

```
$ python main.py 2022-01-01 2022-01-31 --area tokyo

Collecting observation point data...
Saved observation point data. Process time: 1min 9sec
Collecting weather data...
It's takes at least 0min 12sec
Saved weather data. Process time: 0min 16sec
```

### データ取得にかかる時間
上記出力文の"`It's takes at least 0min 12sec`" の部分からデータ取得に必要な時間が分かります。  
この場合は最低でも12秒かかることを示しており、実際にはこれより長い時間がかかります。

__観測地点が多い場合や、取得期間が長い場合はかなりの時間を要する__ ため、このメッセージを見て必要に応じて処理を止めて取得範囲を調整してください。

<br>


### コマンドライン引数
コマンドライン引数は下記のように与えます。

```
$ python main.py {開始日} {終了日} --area {観測エリア名}
```

* 開始日と終了日は "`YYYY-MM-DD`" の形式です。  
* `--area` には観測エリアを指定し、"東京都"の場合"Tokyo"のように都道府県名のローマ字表記（頭文字は大文字）で指定します。  
  指定できる観測エリア一覧は "`$python main.py --help`" で確認できます。  

* `--area` には複数のエリアを指定できます。  
* `--area` は都道府県名の他に地域名 `["Tohoku", "Kanto", "Chubu", "Kinki", "Chugoku", "Shikoku", "Kyushu"]` が指定できます。

<br>

## 保存されるデータ
保存されるデータは下記の2種類です。  

1. `obs_point_data.csv`  
  観測地点の情報をまとめたcsvファイルです。このファイルがすでに存在する場合は保存処理をスキップします。  
  下記のカラムで構成されており、分析など行う場合はこのデータと天気データを組み合わせて使うことになると思います。  

    |      カラム名       |    型    |                                意味                                 |
    | ------------------- | -------- | ------------------------------------------------------------------- |
    | symbol              | str      | "s" or "a", 大きい都市だと"s"になる？                               |
    | prec_num            | int      | 観測地点が属する都道府県に割り当てられた数値                        |
    | point_num           | int      | 観測地点に割り当てられた数値                                        |
    | point_name          | str      | 観測地点名                                                          |
    | point_name_kana     | str      | 観測地点名 (カタカナ)                                               |
    | lat                 | float    | 緯度 (latitude)                                                     |
    | lon                 | float    | 経度 (longitude)                                                    |
    | elevation           | float    | 標高                                                                |
    | obs_areaipitation   | int      | 降水量の観測をしているか                                            |
    | obs_temperature     | int      | 気温の観測をしているか                                              |
    | obs_humidity        | int      | 湿度の観測をしているか                                              |
    | obs_wind            | int      | 風の観測をしているか （0,1に加え、2の場合があるが違いは分からない） |
    | obs_sunshine        | int      | 日照時間の観測をしているか                                          |
    | obs_snowfall        | int      | 降雪量の観測をしているか                                            |
    | obs_from            | datetime | 観測開始日. 入力されていない場合も多い                              |
    | name_change_history | str      | 地域名が変わったことがあるか                                        |
    |                     |          |                                                                     |

2. `weather_point~~~.csv`  
  ある観測地点の指定した期間の天気データをまとめたcsvファイルです。  
  ファイルの命名規則は `weather_point{観測地点No.}_{開始日}_{終了日}.csv` です。  

   |          カラム名          |    型    |             意味             |
   | -------------------------- | -------- | ---------------------------- |
   | date                       | datetime | 日付                         |
   | point_num                  | int      | 観測地点に割り当てられた数値 |
   | atm_onsite                 | float    | 現地の気圧 [hPa]             |
   | atm_sea_level              | float    | 海面の気圧 [mm]              |
   | precip_total               | float    | 合計降水量 [mm]              |
   | precip_max_1h              | float    | 1時間の最大降水量 [mm]       |
   | precip_max_10m             | float    | 10分間の最大降水量 [mm]      |
   | temp_avg                   | float    | 平均気温 [℃]                 |
   | temp_max                   | float    | 最高気温 [℃]                 |
   | temp_min                   | float    | 最低気温 [℃]                 |
   | hum_avg                    | float    | 平均湿度 [%]                 |
   | hum_min                    | float    | 最低湿度 [%]                 |
   | wind_speed_avg             | float    | 平均風速 [m/s]               |
   | wind_speed_max             | float    | 最大風速 [m/s]               |
   | dir_wind_speed_max         | str      | 最大風速の風向き             |
   | max_instantenious_wind     | float    | 最大瞬間風速 [ms]            |
   | dir_max_instantenious_wind | str      | 最大瞬間風速の風向き         |
   | hour_of_sunshine           | float    | 日照時間 [hour]              |
   | snowfall                   | float    | 降雪量 [cm]                  |
   | deepest_snow               | float    | 最深積雪 [cm]                |
   | general_cond_daytime       | str      | 天気概況（昼）               |
   | general_cond_nighttime     | str      | 天気概況（夜）               |
   |                            |          |                              |

<br>

### 天気データに対するデータ処理

取得した天気データの値には様々な付加情報があるため、それに応じた処理を施しています。  
[値欄の記号の説明 (気象庁HP)](https://www.data.jma.go.jp/obd/stats/data/mdrr/man/remark.html)  
  
* データが"--"の場合は0とする.
* 末尾に")"が付いているものは")"を外してそのまま使う.
* 末尾に"]"が付いているものは欠損値とする.
* データが"×"の場合は欠損値とする.
* データが"////"の場合は欠損値とする.
* データが"#"の場合は欠損値とする.
* 末尾に"*"が付いているものは実際に見つけていないのでとりあえずそのままにする.

### 観測地点について