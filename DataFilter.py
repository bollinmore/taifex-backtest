import pandas as pd
import argparse

class DataFilter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None
        self.filtered_data = None

    def load_data(self, encoding='big5'):
        try:
            self.data = pd.read_csv(self.file_path, encoding=encoding)
            print("Data loaded successfully.")
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: The file {self.file_path} was not found.")

    def preprocess_data(self):
        if self.data is not None:
            self.data["商品代號"] = self.data["商品代號"].str.strip()
            self.data["到期月份(週別)"] = self.data["到期月份(週別)"].str.strip()
            self.data["成交日期"] = pd.to_datetime(self.data["成交日期"], format='%Y%m%d')
            self.data["成交時間"] = pd.to_datetime(self.data["成交時間"].astype(str).str.zfill(6), format='%H%M%S').dt.time
            print("Data preprocessed (whitespaces removed, date and time converted).")
        else:
            raise ValueError("Error: Data not loaded. Please load data first.")

    def filter_data(self, product_code, expiry_month, start_date=None, start_time=None):
        if self.data is not None:
            self.filtered_data = self.data[
                (self.data["商品代號"] == product_code) &
                (self.data["到期月份(週別)"] == expiry_month)
            ]
            if start_date and start_time:
                start_date = pd.to_datetime(start_date)
                self.filtered_data = self.filtered_data[
                    (self.filtered_data["成交日期"] >= start_date) &
                    (self.filtered_data["成交時間"] >= start_time)
                ]
            elif start_date or start_time:
                raise ValueError("Both start_date and start_time must be provided together.")

            if self.filtered_data.empty:
                print(f"Warning: No data found for 商品代號={product_code}, 到期月份(週別)={expiry_month} with start date >= {start_date} and start time >= {start_time}.")
            else:
                print(f"Filtered data for 商品代號={product_code}, 到期月份(週別)={expiry_month} with start date >= {start_date} and start time >= {start_time}.")
        else:
            raise ValueError("Error: Data not loaded. Please load data first.")

    def aggregate_data(self):
        if self.filtered_data is not None and not self.filtered_data.empty:
            grouped = self.filtered_data.groupby(["成交日期", "成交時間"]).agg(
                開盤價=("成交價格", "first"),
                收盤價=("成交價格", "last"),
                最高價=("成交價格", "max"),
                最低價=("成交價格", "min")
            ).reset_index()
            self.filtered_data = self.filtered_data.merge(grouped, on=["成交日期", "成交時間"])
            self.filtered_data = self.filtered_data.drop_duplicates(subset=["成交日期", "成交時間"], keep="last")
            print("Data aggregated and merged with computed columns.")
        else:
            raise ValueError("Error: No filtered data available to aggregate.")

    def save_filtered_data(self, output_path="filtered_data.csv", encoding='big5'):
        if self.filtered_data is not None and not self.filtered_data.empty:
            self.filtered_data.to_csv(output_path, index=False, encoding=encoding)
            print(f"Filtered data saved to {output_path}.")
        else:
            raise ValueError("Error: No filtered data available to save.")


def main(args=None):
    parser = argparse.ArgumentParser(description="Filter Taiwan Futures Exchange data.")
    parser.add_argument("-f", "--file_path", required=True, help="Path to the input CSV file.")
    parser.add_argument("-p", "--product_code", required=True, help="Product code to filter, e.g., 'MTX'.")
    parser.add_argument("-e", "--expiry_month", required=True, help="Expiry month to filter, e.g., '202501'.")
    parser.add_argument(
        "-d", "--start_date", 
        help="Start transaction date to filter, e.g., '2024-12-26'. Must be in YYYY-MM-DD format.", 
        type=lambda d: pd.to_datetime(d, format='%Y-%m-%d').date()
    )
    parser.add_argument(
        "-s", "--start_time", 
        help="Start transaction time to filter, e.g., '09:00:00'. Must be in HH:MM:SS format.", 
        type=lambda t: pd.to_datetime(t, format='%H:%M:%S').time()
    )
    parser.add_argument(
        "-o", "--output_path", 
        default="filtered_data.csv", 
        help="Path to save the filtered data. Defaults to 'filtered_data.csv'."
    )
    args = parser.parse_args(args)

    data_filter = DataFilter(args.file_path)
    data_filter.load_data()
    data_filter.preprocess_data()
    data_filter.filter_data(args.product_code, args.expiry_month, args.start_date, args.start_time)
    data_filter.aggregate_data()
    data_filter.save_filtered_data(args.output_path)


if __name__ == "__main__":
    import sys
    try:
        if len(sys.argv) == 1:
            print("Error: Missing required arguments. Use -h or --help for usage information.")
            sys.exit(1)
        main(sys.argv[1:])
    except Exception as e:
        print(f"Error: {e}")
