import os
import subprocess
from datetime import datetime

def get_contract_from_date(date_str):
    """根據日期取得契約 (202501 或 202502)。"""
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    if datetime(2024, 11, 21).date() <= date <= datetime(2024, 12, 18).date():
        return '202412'
    if datetime(2024, 12, 20).date() <= date <= datetime(2025, 1, 15).date():
        return '202501'
    elif datetime(2025, 1, 16).date() <= date <= datetime(2025, 2, 19).date():
        return '202502'
    else:
        return None

def extract_date_from_filename(filename):
    """從檔名中提取日期 (Daily_2025_01_02.csv -> 2025-01-02)。"""
    try:
        # 修正邏輯，正確分割檔名並提取日期部分
        date_part = filename.split('_')[1:]  # 提取檔名中的日期部分，例如 ["2025", "01", "02.csv"]
        date_part = '_'.join(date_part).replace('.csv', '')  # 合併並去掉 .csv，例如 "2025_01_02"
        return datetime.strptime(date_part, '%Y_%m_%d').strftime('%Y-%m-%d')
    except (IndexError, ValueError):
        print(f"無法從檔名提取日期：{filename}")
        return None

def main(skip_download=False):
    # 定義虛擬環境的 Python 路徑
    virtualenv_python = r".venv\Scripts\python.exe"  # 修改為虛擬環境的 Python 路徑

    if not os.path.exists(virtualenv_python):
        print(f"錯誤：無法找到虛擬環境的 Python 執行檔於 {virtualenv_python}")
        return

    # Step 1: 執行下載所有資料（如果未跳過）
    if not skip_download:
        print("執行下載所有資料...")
        subprocess.run([virtualenv_python, 'TaifexDownloader.py', 'all'])

    # 定義下載資料的根目錄
    download_dir = "download"
    dataset_dir = "dataset"  # 定義過濾後資料的輸出目錄
    os.makedirs(dataset_dir, exist_ok=True)

    if not os.path.exists(download_dir):
        print(f"錯誤：下載目錄 {download_dir} 不存在。請確認下載是否成功。")
        return

    # 定義回測結果檔案
    backtest_results_file = "backtest_results.csv"
    if os.path.exists(backtest_results_file):
        os.remove(backtest_results_file)  # 清空舊的回測結果

    # 遍歷下載資料
    for root, dirs, files in os.walk(download_dir):
        for file in files:
            if file.startswith('Daily_') and file.endswith('.csv'):
                csv_path = os.path.join(root, file)
                date_str = extract_date_from_filename(file)
                if not date_str:
                    print(f"跳過無效檔案：{file}")
                    continue

                contract = get_contract_from_date(date_str)
                if not contract:
                    print(f"跳過日期範圍外檔案：{file}")
                    continue

                output_file = os.path.join(dataset_dir, f"{date_str.replace('-', '')}.csv")
                print(f"處理檔案：{file} -> Contract: {contract}, Output: {output_file}")

                # Step 2: 執行 DataFilter.py 過濾資料
                try:
                    subprocess.run([
                        virtualenv_python, 'DataFilter.py',
                        '-f', csv_path,
                        '-p', 'MTX',
                        '-e', contract,
                        '-d', date_str,
                        '-s', '08:45:00',
                        '-o', output_file
                    ], check=True)
                except FileNotFoundError:
                    print("錯誤：無法找到 DataFilter.py 執行檔，請確認檔案是否存在。")
                    return

                # Step 3: 執行 TradingBacktester.py 進行回測
                try:
                    with open(backtest_results_file, "a") as results_file:
                        subprocess.run([
                            virtualenv_python, 'TradingBacktester.py', output_file
                        ], check=True, stdout=results_file)
                except FileNotFoundError:
                    print("錯誤：無法找到 TradingBacktester.py 執行檔，請確認檔案是否存在。")
                    return

    print(f"自動化流程完成，所有回測結果已保存至 {backtest_results_file}。")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="自動化交易回測流程")
    parser.add_argument(
        "--skip-download", action="store_true", help="跳過資料下載流程，只處理現有資料"
    )
    args = parser.parse_args()

    main(skip_download=args.skip_download)
