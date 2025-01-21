import pandas as pd
import os

class TradingBacktester:
    def __init__(self, file_path):
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
        self.last_entry_price = None  # Price of the last executed trade
        self.daily_profit_loss = 0  # Total profit/loss for the day
        self.parent_trade_id = None  # ID of the parent trade
        self.parent_close_time = None  # Close time of the parent trade
        self.trade_id_counter = 0  # Counter for unique trade IDs
        self.safety_distance = 30  # Minimum distance before moving stop-loss

    def load_data(self):
        # Load data from the file, handle different encodings if necessary
        try:
            self.filtered_data = pd.read_csv(self.file_path, encoding='utf-8')
        except UnicodeDecodeError:
            self.filtered_data = pd.read_csv(self.file_path, encoding='big5')
        
        # Rename columns for consistency with the code
        column_mapping = {
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
        for i in range(len(self.filtered_data)):
            current_time = self.filtered_data.loc[i, 'Time']
            current_price = self.filtered_data.loc[i, 'Close']

            # Close all positions if past the cutoff time
            if current_time >= '13:40:00':
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
        actual_entry_price = self.filtered_data.loc[index, 'Close']
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

        # Execute the trade if the price satisfies the entry condition
        if (trade_type == 'Buy' and actual_entry_price >= entry_price) or (trade_type == 'Sell' and actual_entry_price <= entry_price):
            self.trade_id_counter += 1
            is_parent = self.parent_trade_id is None  # Determine if this is a parent trade
            if is_parent:
                self.parent_trade_id = self.trade_id_counter

            self.position_count += self.parent_lot_size if is_parent else 1
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
                'Stop Loss': stop_loss_price
            })

    def check_stop_loss(self, index):
        # Check if the stop-loss conditions are met for any open trades
        current_price = self.filtered_data.loc[index, 'Close']
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
        close_price = self.filtered_data.loc[index, 'Close']
        total_profit_loss = 0
        for trade in self.trades:
            if trade['Close Time'] is None:  # Process only open trades
                profit_loss = (close_price - trade['Entry Price']) * (1 if trade['Type'] == 'Buy' else -1)
                total_profit_loss += profit_loss
                trade['Close Time'] = close_time
                trade['Close Price'] = close_price
                trade['Profit/Loss'] = profit_loss

        # Update daily profit/loss and reset position tracking variables
        self.daily_profit_loss += total_profit_loss
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
            'Stop Loss': None
        })
        self.position_count = 0
        self.parent_close_time = close_time

        # Update reference points after closing all positions
        self.update_reference_points(index)
        self.last_entry_price = None

    def get_results(self):
        # Return the results of all trades as a DataFrame
        return pd.DataFrame(self.trades)

def main(file_path):
    try:
        # Initialize and execute the backtesting process
        backtester = TradingBacktester(file_path)
        backtester.load_data()
        backtester.set_reference_points()
        print(f"區間最高點 (H): {backtester.H}")
        print(f"區間最低點 (L): {backtester.L}")
        print(f"預計作多的成交價格: {backtester.H + backtester.entry_buffer}")
        print(f"預計作空的成交價格: {backtester.L - backtester.entry_buffer}")
        backtester.backtest()
        trades_df = backtester.get_results()
        print(trades_df)
        print(f"Total Profit/Loss for the day: {backtester.daily_profit_loss}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the trading backtest.")
    parser.add_argument("file_path", type=str, help="Path to the filtered.csv file.")

    try:
        args = parser.parse_args()
        main(args.file_path)
    except SystemExit as e:
        print("Error: Please provide a valid file path.")
