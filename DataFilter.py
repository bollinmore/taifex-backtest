import pandas as pd
import argparse

class DataFilter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None
        self.filtered_data = None

    def load_data(self, encoding='big5'):
        """Load the dataset from the file."""
        try:
            self.data = pd.read_csv(self.file_path, encoding=encoding)
            print("Data loaded successfully.")
        except FileNotFoundError:
            print(f"Error: The file {self.file_path} was not found.")
            self.data = None

    def preprocess_data(self):
        """Remove leading and trailing whitespaces in specific columns and convert date and time."""
        if self.data is not None:
            self.data["商品代號"] = self.data["商品代號"].str.strip()
            self.data["到期月份(週別)"] = self.data["到期月份(週別)"].str.strip()
            self.data["成交日期"] = pd.to_datetime(self.data["成交日期"], format='%Y%m%d')
            self.data["成交時間"] = pd.to_datetime(self.data["成交時間"].astype(str).str.zfill(6), format='%H%M%S').dt.time
            print("Data preprocessed (whitespaces removed, date and time converted).")
        else:
            print("Error: Data not loaded. Please load data first.")

    def filter_data(self, product_code, expiry_month):
        """Filter data based on product code and expiry month."""
        if self.data is not None:
            self.filtered_data = self.data[
                (self.data["商品代號"] == product_code) &
                (self.data["到期月份(週別)"] == expiry_month)
            ]
            if self.filtered_data.empty:
                print(f"Warning: No data found for 商品代號={product_code}, 到期月份(週別)={expiry_month}.")
            else:
                print(f"Filtered data for 商品代號={product_code}, 到期月份(週別)={expiry_month}.")
        else:
            print("Error: Data not loaded. Please load data first.")

    def aggregate_data(self):
        """Aggregate data by 成交時間 to compute open, close, high, and low prices."""
        if self.filtered_data is not None and not self.filtered_data.empty:
            grouped = self.filtered_data.groupby(["成交日期", "成交時間"]).agg(
                開盤價=("成交價格", "first"),
                收盤價=("成交價格", "last"),
                最高價=("成交價格", "max"),
                最低價=("成交價格", "min")
            ).reset_index()

            # Merge aggregated data back to the filtered data and keep the last record per time
            self.filtered_data = self.filtered_data.merge(grouped, on=["成交日期", "成交時間"])
            self.filtered_data = self.filtered_data.drop_duplicates(subset=["成交日期", "成交時間"], keep="last")
            print("Data aggregated and merged with computed columns.")
        else:
            print("Error: No filtered data available to aggregate.")

    def save_filtered_data(self, output_path="filtered_data.csv", encoding='big5'):
        """Save the filtered data to a CSV file."""
        if self.filtered_data is not None and not self.filtered_data.empty:
            self.filtered_data.to_csv(output_path, index=False, encoding=encoding)
            print(f"Filtered data saved to {output_path}.")
        else:
            print("Error: No filtered data available to save.")


def main(args=None):
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Filter Taiwan Futures Exchange data.")
    parser.add_argument("-f", "--file_path", required=True, help="Path to the input CSV file.")
    parser.add_argument("-p", "--product_code", required=True, help="Product code to filter, e.g., 'MTX'.")
    parser.add_argument("-e", "--expiry_month", required=True, help="Expiry month to filter, e.g., '202501'.")
    parser.add_argument(
        "-o", "--output_path", 
        default="filtered_data.csv", 
        help="Path to save the filtered data. Defaults to 'filtered_data.csv'."
    )
    args = parser.parse_args(args)

    # Create an instance of DataFilter
    data_filter = DataFilter(args.file_path)
    
    # Process data
    data_filter.load_data()
    data_filter.preprocess_data()
    data_filter.filter_data(args.product_code, args.expiry_month)
    data_filter.aggregate_data()
    
    # Save filtered data
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
