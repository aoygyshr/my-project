import os
from datetime import datetime
import pandas as pd
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_FILE = os.path.join(BASE_DIR, "memory", "01_watchlist", "watchlist.csv")
REPORTS_DIR = os.path.join(BASE_DIR, "memory", "02_reports")
SIGNALS_DIR = os.path.join(BASE_DIR, "memory", "03_signals")


def calculate_rsi(series, period=14):
  delta = series.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
  rs = gain / loss
  return 100 - (100 / (1 + rs))


def analyze_ticker(ticker_code):
  ticker = yf.Ticker(ticker_code)
  df = ticker.history(period="6mo")
  if df.empty:
    return None

  df["MA25"] = df["Close"].rolling(window=25).mean()
  df["MA75"] = df["Close"].rolling(window=75).mean()
  df["RSI"] = calculate_rsi(df["Close"])

  latest = df.iloc[-1]
  prev = df.iloc[-2] if len(df) > 1 else latest

  # シグナル判定ロジック
  signal = "中立 (WAIT)"
  reason = []

  if latest["RSI"] <= 30:
    reason.append(f"RSIが売られすぎ水準 ({latest['RSI']:.1f})")
  elif latest["RSI"] >= 70:
    reason.append(f"RSIが買われすぎ水準 ({latest['RSI']:.1f})")

  if prev["Close"] < prev["MA25"] and latest["Close"] >= latest["MA25"]:
    reason.append("25日移動平均線を上抜け")
  elif prev["Close"] > prev["MA25"] and latest["Close"] <= latest["MA25"]:
    reason.append("25日移動平均線を下抜け")

  if latest["RSI"] <= 35 or (
      prev["Close"] < prev["MA25"] and latest["Close"] >= latest["MA25"]
  ):
    signal = "🟢 買い検討 (BUY CANDIDATE)"
  elif latest["RSI"] >= 70 or (
      prev["Close"] > prev["MA25"] and latest["Close"] <= latest["MA25"]
  ):
    signal = "🔴 売り検討 (SELL CANDIDATE)"

  return {
      "code": ticker_code,
      "date": latest.name.strftime("%Y-%m-%d"),
      "close": round(latest["Close"], 1),
      "ma25": round(latest["MA25"], 1) if pd.notnull(latest["MA25"]) else None,
      "ma75": round(latest["MA75"], 1) if pd.notnull(latest["MA75"]) else None,
      "rsi": round(latest["RSI"], 1) if pd.notnull(latest["RSI"]) else None,
      "signal": signal,
      "reason": " / ".join(reason) if reason else "特段のシグナルなし",
  }


def run():
  if not os.path.exists(WATCHLIST_FILE):
    print("Watchlist not found.")
    return

  watchlist = pd.read_csv(WATCHLIST_FILE)
  today_str = datetime.now().strftime("%Y-%m-%d")

  results = []
  for _, row in watchlist.iterrows():
    code = str(row["code"]).strip()
    name = row.get("name", code)
    print(f"Analyzing {name} ({code})...")
    res = analyze_ticker(code)
    if res:
      res["name"] = name
      results.append(res)

  # レポートMarkdownの生成
  os.makedirs(REPORTS_DIR, exist_ok=True)
  report_path = os.path.join(REPORTS_DIR, f"report_{today_str}.md")

  lines = [
      f"# 📈 株式分析レポート ({today_str})",
      "",
      "> **現場エージェント (Antigravity)** より作戦本部 (Claude Cowork) および CEO へ報告",
      "",
      "| 銘柄コード | 銘柄名 | 現在値 | 25日線 | RSI(14) | 判定シグナル | 判定理由 |",
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
  ]
  for r in results:
    lines.append(
        f"| {r['code']} | {r['name']} | {r['close']} | {r['ma25']} |"
        f" {r['rsi']} | **{r['signal']}** | {r['reason']} |"
    )

  lines.append("")
  lines.append("## 今後の推奨アクション")
  lines.append(
      "- 買い検討銘柄については、作戦本部（Claude"
      " Cowork）にてファンダメンタルズ（決算・業績動向）と照らし合わせ、最終エントリーを判断してください。"
  )

  with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
  print(f"Report saved to {report_path}")

  # 最新シグナルサマリーの保存
  os.makedirs(SIGNALS_DIR, exist_ok=True)
  signals_path = os.path.join(SIGNALS_DIR, "latest_signals.md")
  with open(signals_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
  print(f"Latest signals updated: {signals_path}")


if __name__ == "__main__":
  run()
