import backtrader as bt
import pandas as pd
from datetime import datetime
import sys
import os
sys.path.append('.')
from strategy import hit_limitup_more_volume_double

def less_than_six():
    print('less_than_six')
    cerebro = bt.Cerebro()
    cerebro.addstrategy(hit_limitup_more_volume_double.HitLimitUpMoreVolumeDouble)
    # 构建一个3天的测试数据
    dates = [datetime(2023, 1, i) for i in range(1, 4)]
    data = {
        'open': [10.0, 10.0, 10.0],
        'high': [10.5, 10.5, 10.5],
        'low': [9.5, 9.5, 9.5],
        'close': [10.0, 10.0, 10.0],
        'volume': [1000, 1000, 1000]
    }
    df = pd.DataFrame(data, index=dates)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.run()

def more_than_six():
    print('more_than_six')
    cerebro = bt.Cerebro()
    cerebro.addstrategy(hit_limitup_more_volume_double.HitLimitUpMoreVolumeDouble)
    # 构建一个6天的测试数据
    dates = [datetime(2023, 1, i) for i in range(1, 7)]
    data = {
        'open': [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        'high': [10.5, 10.5, 10.5, 10.5, 10.5, 10.5],
        'low': [9.5, 9.5, 9.5, 9.5, 9.5, 9.5],
        'close': [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        'volume': [1000, 1000, 1000, 1000, 1000, 1000],
        'ts_code': ['000001.SZ'] * 6,
    }
    df = pd.DataFrame(data, index=dates)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.run()

def test_hit_limitup_more_volume_double():
    print('test_hit_limitup_more_volume_double')
    """
    构造满足下面条件的数据：
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
    # 涨停
    limit_up_ratio = 0.1
    # 阴线倍増
    more_volume_ratio = 2.0
    # 小幅回撤
    small_retrace_ratio = 0.001
    base_close = 9.13
    limit_up_close = round(base_close*(1+limit_up_ratio), 2)
    # 构造一个6天的测试数据
    dates = [datetime(2023, 1, i) for i in range(1, 8)]
    data = {
        'open': [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        'high': [10.5, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5],
        'low': [9.5, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5],
        'close': [9.13, limit_up_close, limit_up_close*(1-small_retrace_ratio), limit_up_close*(1-small_retrace_ratio), limit_up_close*(1-small_retrace_ratio), limit_up_close*(1-small_retrace_ratio), limit_up_close*(1-small_retrace_ratio)],
        'volume': [1000,1000, 2100, 1000, 1000, 1000, 1000],
        'ts_code': ['000001.SZ'] * 7,
    }
    df = pd.DataFrame(data,index=dates)
    data = bt.feeds.PandasData(dataname=df,nocase=True)
    cerebro = bt.Cerebro()
    cerebro.addstrategy(hit_limitup_more_volume_double.HitLimitUpMoreVolumeDouble, limitup_ratio=0.1, volume_ratio=2.0, decrease_ratio=0.03)
    cerebro.adddata(data)
    cerebro.run()
    

if __name__ == '__main__':
    less_than_six()
    more_than_six()
    test_hit_limitup_more_volume_double()
