import argparse
import shioaji as sj
from datetime import datetime

class AutoTrader:
    def __init__(self, args):
        self.args = args
        self.api = None
        self.contract = None

    def initialize_api(self):
        print("登入中...")
        self.api = sj.Shioaji(simulation=self.args.sandbox)
        self.api.login(api_key=self.args.api_key, secret_key=self.args.api_secret)
        print("成功登入！")
        print("啟動電子應用憑證...")
        self.api.activate_ca(ca_path=self.args.ca_path, ca_passwd=self.args.ca_passwd, person_id=self.args.person_id)
        print("電子應用憑證驗證成功！")

    def get_contract(self):
        print(f"取得期貨合約：{self.args.contract}...")
        self.contract = self.api.Contracts.Futures.TXF['\u8fd1\u6708']
        if not self.contract:
            raise ValueError("無法找到對應的期貨合約！")
        print("成功取得期貨合約！")

    def place_order(self, action, price, quantity):
        print(f"開始下單：動作={action}, \u50f9\u683c={price}, \u6578\u91cf={quantity}...")
        order = self.api.Order(
            price=price,
            quantity=quantity,
            action=sj.constant.Action.Buy if action == 'buy' else sj.constant.Action.Sell,
            price_type=sj.constant.FuturesPriceType.LMT,
            order_type=sj.constant.OrderType.ROD,
            octype=sj.constant.FuturesOCType.Auto,
            account=self.api.futopt_account
        )
        trade = self.api.place_order(self.contract, order)
        print("下單成功！")
        print("交易資訊：", trade)

    def monitor_price_and_trade(self):
        def quote_callback(exchange, tick):
            current_price = tick.close
            print(f"{datetime.now()} | 行情更新：現價={current_price}")
            if self.args.action == 'buy' and current_price <= self.args.trigger_price:
                print("觸發買入條件！")
                self.place_order(self.args.action, self.args.price, self.args.quantity)
                self.api.quote.unsubscribe(self.contract, quote_type=sj.constant.QuoteType.Tick)
            elif self.args.action == 'sell' and current_price >= self.args.trigger_price:
                print("觸發賣出條件！")
                self.place_order(self.args.action, self.args.price, self.args.quantity)
                self.api.quote.unsubscribe(self.contract, quote_type=sj.constant.QuoteType.Tick)

        print("訂閱即時行情...")
        self.api.quote.set_on_tick_fop_v1_callback(quote_callback)
        self.api.quote.subscribe(self.contract, quote_type=sj.constant.QuoteType.Tick)
        print("開始監控行情，等待觸發條件...")

def parse_args():
    parser = argparse.ArgumentParser(description="\u6c38\u8c50\u91d1\u8b49\u5238 API \u81ea\u52d5\u4e0b\u55ae\u7a0b\u5f0f")
    parser.add_argument('--contract', type=str, default="TXF", help="\u671f\u8ca8\u5408\u7d04\u4ee3\u78bc\uff0c\u9810\u8a2d\u70ba\u5c0f\u53f0\u6307 (TXF)")
    parser.add_argument('--price', type=float, required=True, help="\u4e0b\u55ae\u50f9\u683c")
    parser.add_argument('--trigger_price', type=float, required=True, help="\u89f8\u767c\u50f9\u683c")
    parser.add_argument('--quantity', type=int, default=1, help="\u4e0b\u55ae\u6578\u91cf\uff0c\u9810\u8a2d\u70ba 1")
    parser.add_argument('--action', type=str, choices=['buy', 'sell'], required=True, help="\u8cb7\u5165 (buy) \u6216\u8ce3\u51fa (sell)")
    parser.add_argument('--ca_path', type=str, required=True, help="\u96fb\u5b50\u61c9\u7528\u6191\u8b49\u8def\u5f91 (.pfx \u6a94)")
    parser.add_argument('--ca_passwd', type=str, required=True, help="\u96fb\u5b50\u61c9\u7528\u6191\u8b49\u5bc6\u78bc")
    parser.add_argument('--api_key', type=str, required=True, help="API Key")
    parser.add_argument('--api_secret', type=str, required=True, help="API Secret")
    parser.add_argument('--person_id', type=str, required=True, help="\u8eab\u4efd\u8b49\u5b57\u865f")
        parser.add_argument('--sandbox', action='store_true', help="啟用沙盒模式進行測試")
    return parser.parse_args()

def main():
    args = parse_args()
    trader = AutoTrader(args)
    trader.initialize_api()
    trader.get_contract()
    trader.monitor_price_and_trade()

if __name__ == "__main__":
    main()
