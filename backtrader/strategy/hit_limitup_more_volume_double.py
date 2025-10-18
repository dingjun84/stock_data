import backtrader as bt

class HitLimitUpMoreVolumeDouble(bt.Strategy):

    def __init__(self, limitup_ratio=0.1, volume_ratio=2.0, decrease_ratio=0.03):
        self.limitup_ratio = limitup_ratio
        self.volume_ratio = volume_ratio
        self.decrease_ratio = decrease_ratio
        print(f"limitup_ratio: {self.limitup_ratio}, volume_ratio: {self.volume_ratio}, decrease_ratio: {self.decrease_ratio}")

    def is_limit_up(self,open:float,close:float,limitup_ratio:float):
        # 涨停：四舍五入，保留两位小数 open * (1 + limitup_ratio)
        # print(f'is_limit_up open: {open}, close: {close}, limitup_ratio: {limitup_ratio}, 涨停: {round(open * (1 + limitup_ratio), 2)}')
        return close >= round(open * (1 + limitup_ratio), 2)

    

    def next(self):
        """
        # 涨停
        # 五天前收盘价大于6天前收盘价的9.9%(涨停，创业板，科创板按20%-30%算)

        # 阴线倍増
        # 四天前成交量不低于五天前成交量的2倍
        # 四天前收盘价低于五天前收盘价的0.1%

        # 小幅回撤
        # -天前收盘价不低于五天前收盘价的3% 小幅波动
        # 二天前收盘价不低于五天前收盘价的3% 小幅波动
        # 三天前收盘价不低于五天前收盘价的3% 小幅波动

        """
        if len(self.datas[0].close) < 6:
            # print(f'日期 {self.datas[0].datetime.date(0)} 数据不足，无法计算')
            return False
        # print(f'日期 {self.datas[0].datetime.date(0)} close[-6]: {self.datas[0].close[-6]}, close[-5]: {self.datas[0].close[-5]},close[-4]: {self.datas[0].close[-4]},close[-3]: {self.datas[0].close[-3]},close[-2]: {self.datas[0].close[-2]},close[-1]: {self.datas[0].close[-1]}')
        # 涨停
        limit_up_bool = self.is_limit_up(open=self.datas[0].close[-6] , close=self.datas[0].close[-5], limitup_ratio=self.limitup_ratio)
        
        # 阴线倍増
        volume_double_bool = self.datas[0].volume[-4] >= self.datas[0].volume[-5] * self.volume_ratio
        close_diff_bool = self.datas[0].close[-4] <= self.datas[0].close[-5] * (1 - 0.001)
        
        # 小幅回撤
        close_diff_3_bool = self.datas[0].close[-3] >= self.datas[0].close[-5] * (1 - self.decrease_ratio)
        close_diff_2_bool = self.datas[0].close[-2] >= self.datas[0].close[-5] * (1 - self.decrease_ratio)
        close_diff_1_bool = self.datas[0].close[-1] >= self.datas[0].close[-5] * (1 - self.decrease_ratio)
        
        # 打印所有条件
        # print(f'日期 {self.datas[0].datetime.date(0)} 涨停: {limit_up_bool}, 阴线倍増: {volume_double_bool}, 四天前收盘价低于五天前收盘价的0.1%: {close_diff_bool}, 小幅回撤: {close_diff_3_bool and close_diff_2_bool and close_diff_1_bool}')

        # 所有条件都满足
        if limit_up_bool and volume_double_bool and close_diff_bool and close_diff_3_bool and close_diff_2_bool and close_diff_1_bool:
            self.buy(size=100)
            print(f'，日期 {self.datas[0].datetime.date(0)} 购买价格 {self.data.open[0]}')
        
        