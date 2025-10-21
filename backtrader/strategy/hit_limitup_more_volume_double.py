import backtrader as bt

class HitLimitUpMoreVolumeDouble(bt.Strategy):

    def __init__(self, limitup_ratio=0.1, volume_ratio=2.0, decrease_ratio=0.03,trade_size=100):
        self.limitup_ratio = limitup_ratio
        self.volume_ratio = volume_ratio
        self.decrease_ratio = decrease_ratio
        self.trade_size = trade_size
        print(f"limitup_ratio: {self.limitup_ratio}, volume_ratio: {self.volume_ratio}, decrease_ratio: {self.decrease_ratio}, trade_size: {self.trade_size}")

        self.order = None

         # Indicators for the plotting show
        bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        bt.indicators.WeightedMovingAverage(self.datas[0], period=25,
                                            subplot=True)
        bt.indicators.StochasticSlow(self.datas[0])
        bt.indicators.MACDHisto(self.datas[0])
        rsi = bt.indicators.RSI(self.datas[0])
        bt.indicators.SmoothedMovingAverage(rsi, period=10)
        bt.indicators.ATR(self.datas[0], plot=False)


    def is_limit_up(self,open:float,close:float,limitup_ratio:float):
        # 涨停：四舍五入，保留两位小数 open * (1 + limitup_ratio)
        # print(f'is_limit_up open: {open}, close: {close}, limitup_ratio: {limitup_ratio}, 涨停: {round(open * (1 + limitup_ratio), 2)}')
        return close >= round(open * (1 + limitup_ratio), 2)

    

    def next(self):
        """
        # 涨停
        # 四天前收盘价大于五天前收盘价的9.9%(涨停，创业板，科创板按20%-30%算)

        # 阴线倍増
        # 三天前成交量不低于四天前成交量的2倍
        # 三天前收盘价低于四天前收盘价的0.1%

        # 小幅回撤
        # 当天收盘价不低于四天前收盘价的3% 小幅波动
        # 一天前收盘价不低于四天前收盘价的3% 小幅波动
        # 二天前收盘价不低于四天前收盘价的3% 小幅波动

        """
        if len(self.datas[0].close) < 6:
            # print(f'日期 {self.datas[0].datetime.date(0)} 数据不足，无法计算')
            return False
        # print(f'日期 {self.datas[0].datetime.date(0)} close[-6]: {self.datas[0].close[-6]}, close[-5]: {self.datas[0].close[-5]},close[-4]: {self.datas[0].close[-4]},close[-3]: {self.datas[0].close[-3]},close[-2]: {self.datas[0].close[-2]},close[-1]: {self.datas[0].close[-1]}')
        # 涨停
        limit_up_bool = self.is_limit_up(open=self.datas[0].close[-5] , close=self.datas[0].close[-4], limitup_ratio=self.limitup_ratio)
        
        # 阴线倍増
        volume_double_bool = self.datas[0].volume[-3] >= self.datas[0].volume[-4] * self.volume_ratio
        close_diff_bool = self.datas[0].close[-3] <= self.datas[0].close[-4] * (1 - 0.001)
        
        # 小幅回撤
        close_diff_3_bool = self.datas[0].close[-2] >= self.datas[0].close[-4] * (1 - self.decrease_ratio)
        close_diff_2_bool = self.datas[0].close[-1] >= self.datas[0].close[-4] * (1 - self.decrease_ratio)
        close_diff_1_bool = self.datas[0].close[0] >= self.datas[0].close[-4] * (1 - self.decrease_ratio)
        
        # 打印所有条件

        # print(f'日期 {self.datas[0].datetime.date(0)} 涨停: {limit_up_bool}, 阴线倍増: {volume_double_bool}, 四天前收盘价低于五天前收盘价的0.1%: {close_diff_bool}, 小幅回撤: {close_diff_3_bool and close_diff_2_bool and close_diff_1_bool}')
        if self.position.size > 0 or self.order:
            print(self.position,self.order)
        # 所有条件都满足
        if not self.order and limit_up_bool and volume_double_bool and close_diff_bool and close_diff_3_bool and close_diff_2_bool and close_diff_1_bool:
            self.order =self.buy(size=self.trade_size,exectype=bt.Order.Market)
            print(f'买入信号，日期 {self.datas[0].datetime.date(0)} 购买价格 {self.data.open[0]}')
            return True
        
        # todo:先简单处理，上涨20%，或下跌8%，则卖出
        if self.position and self.position.size >0 and (self.datas[0].close[0] >= self.position.price * (1 + 0.2) ):
            self.order = self.sell(size=self.position.size,exectype=bt.Order.Market)
            print(f'盈利卖出 日期 {self.datas[0].datetime.date(0)} 卖出价格 {self.datas[0].close[0]}')
            return False
        
        if self.position and self.position.size >0 and (self.datas[0].close[0] <= self.position.price * (1 - 0.08)):
            self.order = self.sell(size=self.trade_size,exectype=bt.Order.Market)
            print(f'亏损卖出 日期 {self.datas[0].datetime.date(0)} 卖出价格 {self.datas[0].close[0]}')
            return False

    def notify_order(self, order):
        # if order.status in [order.Submitted, order.Accepted]:
        #     print(f'日期 {self.datas[0].datetime.date(0)} 订单已提交/已接受，等待执行，持仓:{self.position}')
        #     return False

        if order.status in [order.Completed,order.Submitted, order.Accepted]:
            if order.isbuy():
                print(f'日期 {self.datas[0].datetime.date(0)} 购买价格 {order.executed.price}，购买数量 {order.executed.size}，购买佣金 {order.executed.comm}')
            elif order.issell():
                print(f'日期 {self.datas[0].datetime.date(0)} 卖出价格 {order.executed.price}，卖出数量 {order.executed.size}，卖出佣金 {order.executed.comm}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'日期 {self.datas[0].datetime.date(0)} 订单取消/保证金不足/拒绝')
        
        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            print(f'日期 {self.datas[0].datetime.date(0)} 交易关闭，交易毛利润 {trade.pnl}，交易净利润 {trade.pnlcomm}')