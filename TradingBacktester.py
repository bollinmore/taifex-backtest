import pandas as pd
import os

class TradingBacktester:
    def __init__(self, file_path):
        self.file_path = file_path
        self.filtered_data = None
        self.trades = []
        self.H = None
        self.L = None
        self.balance = 400000  # 初始資金
        self.entry_buffer = 10  # 進場價的緩衝點數
        self.stop_loss = 30  # 停損點數
        self.position_count = 0  # 當前持倉口數
        self.max_positions = 4  # 最大持倉口數
        self.last_entry_price = None  # 最後一筆進場價格
        self.daily_profit_loss = 0  # 當日總損益
        self.parent_trade_id = None  # 母單ID
        self.parent_close_time = None  # 母單平倉時間
        self.trade_id_counter = 0  # 交易ID計數器
        self.safety_distance = 30  # 安全距離初始值

    def load_data(self):
        # 嘗試使用多種編碼讀取資料
        try:
            self.filtered_data = pd.read_csv(self.file_path, encoding='utf-8')
        except UnicodeDecodeError:
            self.filtered_data = pd.read_csv(self.file_path, encoding='big5')
        
        # 重新命名欄位以統一格式
        column_mapping = {
            '收盤價': 'Close',
            '最低價': 'Low',
            '成交時間': 'Time',
            '最高價': 'High',
            '開盤價': 'Open'
        }
        self.filtered_data.rename(columns=column_mapping, inplace=True)

    def set_reference_points(self):
        # 設定早盤參考點 (08:45:00 - 09:04:59 的最高價和最低價)
        filtered_time_data = self.filtered_data[(self.filtered_data['Time'] >= '08:45:00') & (self.filtered_data['Time'] <= '09:04:59')]
        self.H = filtered_time_data['High'].max()
        self.L = filtered_time_data['Low'].min()

    def backtest(self):
        # 從 09:05:00 開始交易
        start_index = self.filtered_data[self.filtered_data['Time'] > '09:05:00'].index[0]
        for i in range(start_index, len(self.filtered_data)):
            current_time = self.filtered_data.loc[i, 'Time']
            prev_high = self.filtered_data.loc[i - 1, 'High']
            prev_low = self.filtered_data.loc[i - 1, 'Low']

            # 避免在 13:40:00 之後交易
            if current_time >= '13:40:00':
                self.close_all_positions(i)
                break

            # 根據條件進行買入或賣出
            if prev_high > self.H and self.position_count < self.max_positions:
                self.execute_trade(i, 'Buy', self.H + self.entry_buffer)
            elif prev_low < self.L and self.position_count < self.max_positions:
                self.execute_trade(i, 'Sell', self.L - self.entry_buffer)

            # 檢查是否觸及停損點
            if self.position_count > 0:
                self.check_stop_loss(i)

    def execute_trade(self, index, trade_type, entry_price):
        # 找到實際的成交價格
        actual_entry_price = self.filtered_data.loc[index, 'Close']
        take_profit = actual_entry_price + self.stop_loss if trade_type == 'Buy' else actual_entry_price - self.stop_loss
        stop_loss_price = actual_entry_price - self.stop_loss if trade_type == 'Buy' else actual_entry_price + self.stop_loss

        # 確保加碼邏輯正確：母單平倉後不允許加碼，前一筆必須超過安全距離
        if self.parent_close_time is not None and self.filtered_data.loc[index, 'Time'] >= self.parent_close_time:
            self.parent_trade_id = None  # 重置母單ID，因為母單已平倉
            self.parent_close_time = None  # 重置母單平倉時間

        # 如果是第一次交易，初始化 last_entry_price
        if self.last_entry_price is None:
            self.last_entry_price = actual_entry_price

        # 加碼條件檢查
        if trade_type == 'Buy' and (actual_entry_price - self.last_entry_price) <= self.safety_distance:
            return  # 不符合加碼條件
        elif trade_type == 'Sell' and (self.last_entry_price - actual_entry_price) <= self.safety_distance:
            return  # 不符合加碼條件

        # 建立新交易
        if (trade_type == 'Buy' and actual_entry_price >= entry_price) or (trade_type == 'Sell' and actual_entry_price <= entry_price):
            self.trade_id_counter += 1
            is_parent = self.parent_trade_id is None  # 當前無母單則為新母單
            if is_parent:
                self.parent_trade_id = self.trade_id_counter

            self.position_count += 1
            self.last_entry_price = actual_entry_price

            # 紀錄交易
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
        current_price = self.filtered_data.loc[index, 'Close']
        for trade in self.trades:
            if trade['Close Time'] is None:  # 檢查未平倉的交易
                trade_type = trade['Type']
                stop_loss_price = trade['Stop Loss']

                # 停損檢查
                if (trade_type == 'Buy' and current_price <= stop_loss_price) or \
                   (trade_type == 'Sell' and current_price >= stop_loss_price):
                    self.close_all_positions(index)
                    break

    def close_all_positions(self, index):
        # 平倉所有部位
        close_time = self.filtered_data.loc[index, 'Time']
        close_price = self.filtered_data.loc[index, 'Close']
        total_profit_loss = 0
        for trade in self.trades:
            if trade['Close Time'] is None:  # 計算每筆未平倉交易的盈虧
                profit_loss = (close_price - trade['Entry Price']) * (1 if trade['Type'] == 'Buy' else -1)
                total_profit_loss += profit_loss
                trade['Close Time'] = close_time
                trade['Close Price'] = close_price
                trade['Profit/Loss'] = profit_loss

        self.daily_profit_loss += total_profit_loss  # 更新每日總盈虧
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
        self.parent_close_time = close_time  # 更新母單的平倉時間

    def get_results(self):
        return pd.DataFrame(self.trades)

# 主函數
def main(file_path):
    try:
        backtester = TradingBacktester(file_path)
        backtester.load_data()
        backtester.set_reference_points()
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
    
    # 預設參數設置，用於防止 SystemExit
    try:
        args = parser.parse_args()
        main(args.file_path)
    except SystemExit as e:
        print("Error: Please provide a valid file path.")
