# 四臂收折幾何模擬

計算理想平面中四支等長機臂收折時的外廓尺寸、全角度區間內六對槳盤的最小間距，以及假設的同步和不同步動作。可調整臂長、轉軸間距、槳徑與位置誤差，產出 CSV、執行參數和 Markdown 報告。附帶的設定使用虛構的示範數值。

## 執行

使用 Python 3.9 或以上版本，並備妥 Asia/Taipei 時區資料。只產生數據與報告時，使用 Python 標準函式庫即可。

```sh
python3 run_analysis.py --no-plots --output output
```

在具有 Arial Unicode 的 macOS 上，可安裝繪圖套件後另外產生繁體中文 PNG 和 SVG。

```sh
python3 -m pip install -r requirements.txt
python3 run_analysis.py --output output
```

每次執行會另建一個輸出目錄。以 `--config` 選取另一份 JSON 設定，或複製 `設定.json` 後調整尺寸與角度。

模型把槳盤視為共平面圓盤。時間序列取樣自五次平滑軌跡，代表所設定的動作規劃。若要用於實機，仍須另外量測伺服負載、結構、氣流與飛行響應。
