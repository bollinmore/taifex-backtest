import pandas as pd
import os

class TradingBacktester:
    def __init__(self, file_path=None, verbose=False, update_reference=False):
        self.file_path = file_path  # Path to the input data file
        self.filtered_data = None  # DataFrame to store loaded data
        self.trades = []  # List to store executed trades
        self.H = None  # High price reference point
        self.L = None  # Low price reference point
        self.balance = 400000  # Initial balance in trading account
        self.entry_buffer = 10  # Entry price buffer in points
        self.stop_loss = 30  # Stop-loss threshold in points
        self.position_count = 0  # Current number of open positions
        self.max_positions = 4  # Maximum allowable positions
        self.parent_lot_size = 2  # Initial number of lots for parent trades
        self.loss_count = 0  # Counter for the number of stop-loss hits
        self.daily_loss_limit = 180  # Daily loss limit in points
        self.cumulative_loss = 0  # Cumulative loss for the day
        self.last_entry_price = None  # Price of the last executed trade
        self.daily_profit_loss = 0  # Total profit/loss for the day
        self.parent_trade_id = None  # ID of the parent trade
        self.parent_close_time = None  # Close time of the parent trade
        self.trade_id_counter = 0  # Counter for unique trade IDs
        self.safety_distance = 30  # Minimum distance before moving stop-loss
        self.verbose = verbose  # Control whether to print detailed output
        self.update_reference = update_reference  # Control whether to update reference points every minute

    def load_data(self, file_path):
        # Load data from the file, handle different encodings if necessary
        try:
            self.filtered_data = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            self.filtered_data = pd.read_csv(file_path, encoding='big5')
        
        # Rename columns for consistency with the code
        column_mapping = {
            '成交價格': 'Price',
            '收盤價': 'Close',
            '最低價': 'Low',
            '成交時間': 'Time',
            '最高價': 'High',
            '開盤價': 'Open'
        }
        self.filtered_data.rename(columns=column_mapping, inplace=True)

    def set_reference_points(self):
        # Set the high and low points from the first 20 minutes of data
        filtered_time_data = self.filtered_data[(self.filtered_data['Time'] >= '08:45:00') & (self.filtered_data['Time'] <= '09:04:59')]
        self.H = filtered_time_data['High'].max()
        self.L = filtered_time_data['Low'].min()

    def update_reference_points(self, end_index):
        # Update the high and low points based on data up to a specific index
        current_data = self.filtered_data.iloc[:end_index + 1]
        self.H = current_data['High'].max()
        self.L = current_data['Low'].min()

    def backtest(self):
        # Perform the backtesting loop
        start_index = self.filtered_data[self.filtered_data['Time'] >= '09:05:00'].index[0]
        for i in range(start_index, len(self.filtered_data)):
            current_time = self.filtered_data.loc[i, 'Time']
            current_price = self.filtered_data.loc[i, 'Price']

            # Update reference points every minute if enabled
            if self.update_reference and i > 0 and current_time[:5] != self.filtered_data.loc[i - 1, 'Time'][:5]:
                self.update_reference_points(i)

            # Stop trading if cumulative loss exceeds or equals daily limit
            if self.cumulative_loss >= self.daily_loss_limit:
                if self.verbose:
                    print(f"Daily loss limit reached. Cumulative loss: {self.cumulative_loss}")
                break

            # Close all positions if past the cutoff time
            if current_time >= '13:40:00' and self.position_count > 0:
                self.close_all_positions(i)
                break

            # Check if conditions for entering trades are met
            if current_price >= self.H + self.entry_buffer and self.position_count < self.max_positions:
                self.execute_trade(i, 'Buy', self.H + self.entry_buffer)
            elif current_price <= self.L - self.entry_buffer and self.position_count < self.max_positions:
                self.execute_trade(i, 'Sell', self.L - self.entry_buffer)

            # Check for stop-loss conditions if positions are open
            if self.position_count > 0:
                self.check_stop_loss(i)

    def execute_trade(self, index, trade_type, entry_price):
        # Execute a trade if conditions are met
        actual_entry_price = self.filtered_data.loc[index, 'Price']
        take_profit = actual_entry_price + self.stop_loss if trade_type == 'Buy' else actual_entry_price - self.stop_loss
        stop_loss_price = actual_entry_price - self.stop_loss if trade_type == 'Buy' else actual_entry_price + self.stop_loss

        # Reset parent trade variables if the parent trade was closed
        if self.parent_close_time is not None and self.filtered_data.loc[index, 'Time'] >= self.parent_close_time:
            self.parent_trade_id = None
            self.parent_close_time = None

        # Ensure trades adhere to the safety distance rule
        if self.last_entry_price is not None:
            if trade_type == 'Buy' and (actual_entry_price - self.last_entry_price) <= self.safety_distance:
                return
            elif trade_type == 'Sell' and (self.last_entry_price - actual_entry_price) <= self.safety_distance:
                return

        # Determine lot size based on loss count
        is_parent = self.parent_trade_id is None  # Determine if this is a parent trade
        lot_size = 1 if self.loss_count >= 2 else self.parent_lot_size if is_parent else 1

        # Execute the trade if the price satisfies the entry condition
        if (trade_type == 'Buy' and actual_entry_price >= entry_price) or (trade_type == 'Sell' and actual_entry_price <= entry_price):
            self.trade_id_counter += 1
            if is_parent:
                self.parent_trade_id = self.trade_id_counter

            self.position_count += lot_size
            self.last_entry_price = actual_entry_price

            # Record the trade details
            self.trades.append({
                'Trade ID': self.trade_id_counter,
                'Parent Trade ID': None if is_parent else self.parent_trade_id,
                'Entry Time': self.filtered_data.loc[index, 'Time'],
                'Type': trade_type,
                'Entry Price': actual_entry_price,
                'Close Time': None,
                'Close Price': None,
                'Profit/Loss': None,
                'Take Profit': take_profit,
                'Stop Loss': stop_loss_price,
                'Lot Size': lot_size
            })

    def check_stop_loss(self, index):
        # Check if the stop-loss conditions are met for any open trades
        current_price = self.filtered_data.loc[index, 'Price']
        for trade in self.trades:
            if trade['Close Time'] is None:  # Only check open trades
                trade_type = trade['Type']
                stop_loss_price = trade['Stop Loss']

                # Adjust the stop-loss price to ensure break-even or better
                if (trade_type == 'Buy' and current_price - trade['Entry Price'] > self.safety_distance):
                    trade['Stop Loss'] = trade['Entry Price'] + 1
                elif (trade_type == 'Sell' and trade['Entry Price'] - current_price > self.safety_distance):
                    trade['Stop Loss'] = trade['Entry Price'] - 1

                # Close the trade if the stop-loss is triggered
                if (trade_type == 'Buy' and current_price <= trade['Stop Loss']) or \
                   (trade_type == 'Sell' and current_price >= trade['Stop Loss']):
                    self.close_all_positions(index)
                    break

    def close_all_positions(self, index):
        # Close all open positions and calculate profit/loss
        close_time = self.filtered_data.loc[index, 'Time']
        close_price = self.filtered_data.loc[index, 'Price']
        total_profit_loss = 0
        for trade in self.trades:
            if trade['Close Time'] is None:  # Process only open trades
                profit_loss = (close_price - trade['Entry Price']) * (1 if trade['Type'] == 'Buy' else -1) * trade['Lot Size']
                total_profit_loss += profit_loss
                trade['Close Time'] = close_time
                trade['Close Price'] = close_price
                trade['Profit/Loss'] = profit_loss

        # Update daily profit/loss and cumulative loss
        self.daily_profit_loss += total_profit_loss
        self.cumulative_loss += max(0, -total_profit_loss)  # Only add losses to cumulative loss

        if total_profit_loss < 0:
            self.loss_count += 1

        self.trades.append({
            'Trade ID': None,
            'Parent Trade ID': None,
            'Entry Time': None,
            'Type': 'Close All',
            'Entry Price': None,
            'Close Time': close_time,
            'Close Price': close_price,
            'Profit/Loss': total_profit_loss,
            'Take Profit': None,
            'Stop Loss': None,
            'Lot Size': None
        })
        self.position_count = 0
        self.parent_close_time = close_time

        # Update reference points after closing all positions
        self.update_reference_points(index)
        self.last_entry_price = None

    def get_results(self):
        # Return the results of all trades as a DataFrame
        return pd.DataFrame(self.trades)

def save_trades_to_csv(trades_df, file_name):
    # Ensure the output directory exists
    output_dir = "backtest"
    os.makedirs(output_dir, exist_ok=True)

    # Save the trades DataFrame to the specified file
    output_file = os.path.join(output_dir, f"{file_name.split('.')[0]}-tradelog.csv")
    trades_df.to_csv(output_file, index=False)

def process_single_file(file_path, verbose):
    backtester = TradingBacktester(verbose=verbose)
    backtester.load_data(file_path)
    backtester.set_reference_points()

    if verbose:
        print(f"Processing file: {os.path.basename(file_path)}")
        print(f"區間最高點 (H): {backtester.H}")
        print(f"區間最低點 (L): {backtester.L}")
        print(f"預計作多的成交價格: {backtester.H + backtester.entry_buffer}")
        print(f"預計作空的成交價格: {backtester.L - backtester.entry_buffer}")

    backtester.backtest()
    trades_df = backtester.get_results()

    print(f"Total Profit/Loss for {os.path.basename(file_path)}: {backtester.daily_profit_loss}")

    # Print detailed trade information if verbose is enabled
    if verbose:
        print("Trade Details:")
        print(trades_df)

    # Save trades to a CSV file
    save_trades_to_csv(trades_df, os.path.basename(file_path))

    return backtester.daily_profit_loss, trades_df

def process_folder(folder_path, verbose):
    all_results = {}

    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            file_path = os.path.join(folder_path, file_name)
            daily_profit_loss, trades_df = process_single_file(file_path, verbose)
            if not trades_df.empty:
                all_results[file_name] = (daily_profit_loss, trades_df)

    total_profit_loss = sum(profit_loss for profit_loss, _ in all_results.values())
    print(f"\nTotal Profit/Loss for all files: {total_profit_loss}")
    return all_results

def main(path, is_folder=False, verbose=False):
    try:
        if is_folder:
            process_folder(path, verbose)
        else:
            process_single_file(path, verbose)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the trading backtest on a file or all CSV files in a folder.")
    parser.add_argument("path", type=str, help="Path to the file or folder.")
    parser.add_argument("--folder", action="store_true", help="Specify if the path is a folder containing multiple CSV files.")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed output.")

    try:
        args = parser.parse_args()
        main(args.path, is_folder=args.folder, verbose=args.verbose)
    except SystemExit as e:
        print("Error: Please provide a valid path.")
