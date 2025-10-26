import backtrader as bt
import sys
import time
import os 
import pandas as pd
sys.path.append('.')
from strategy import simple_buy_sell_strategy


"""
tushare数据格式
ts_code	str	股票代码
trade_date	str	交易日期
open	float	开盘价
high	float	最高价
low	float	最低价
close	float	收盘价
pre_close	float	昨收价【除权价，前复权】
change	float	涨跌额
pct_chg	float	涨跌幅 【基于除权后的昨收计算的涨跌幅：（今收-除权昨收）/除权昨收 】
vol	float	成交量 （手）
amount	float	成交额 （千元）
==========================================
backtrader数据格式
open	float	开盘价
high	float	最高价
low	float	最低价
close	float	收盘价
volume	float	成交量 （手）
openinterest	float	成交额 （千元）
"""

# 3. 数据格式转换
def tushare2backtrader(df):
    # 转换日期格式：Tushare 是字符串（如 '20200101'），需转为 datetime 并设为索引
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df = df.set_index('trade_date')
    
    # 调整列顺序与命名，Backtrader 要求的字段顺序为：open, high, low, close, volume, openinterest
    df = df.rename(columns={
        'vol': 'volume',       # 成交量字段名映射
        'amount': 'openinterest',  # 成交额映射到 openinterest（若不需要可设为 0）
        'ts_code': 'code',
    })
    
    # 确保字段顺序正确（Backtrader 按此顺序读取）
    df = df[['open', 'high', 'low', 'close', 'volume', 'openinterest', 'code']]
    
    # 按日期升序排列（回测需时间正序）
    df = df.sort_index(ascending=True)
    
    return df

if __name__ == '__main__':

    # ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount

   
    df = pd.read_csv(f'stock_datas/test_data/test_data1.csv', parse_dates=True)
            
    # 将tushare格式的数据转换为backtrader兼容的格式
    df = tushare2backtrader(df)
    
    # 创建backtrader数据对象，用于向Cerebro引擎提供数据
    data = bt.feeds.PandasData(dataname=df)
    
    # 创建回测引擎实例
    cerebro = bt.Cerebro()
    
    # 添加测试策略到回测引擎
    cerebro.addstrategy(simple_buy_sell_strategy.TestStrategy)
    # 添加夏普比率分析器（内置）
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',timeframe=bt.TimeFrame.Days, riskfreerate=0.03)
    
    # 添加数据到回测引擎
    cerebro.adddata(data)
    
    # 设置每次交易的固定仓位大小为100股
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)
    
    # 设置初始资金为100万元
    cerebro.broker.set_cash(1000000)
    
    # 设置佣金率为0.03%（万分之三）
    cerebro.broker.setcommission(commission=0.0003)
    
    results = cerebro.run()
    my_strategy = results[0]
    # 打印夏普比率
    print(f"夏普比率: {my_strategy.analyzers.sharpe.get_analysis()['sharperatio']}")

    # 打印胜负次率
    print(f"胜负率：{round(my_strategy.win_count*100.0 / (my_strategy.win_count + my_strategy.loss_count), 2)}% 胜利次数: {my_strategy.win_count}，失败次数: {my_strategy.loss_count}，总交易次数: {my_strategy.win_count + my_strategy.loss_count}")


    # sleep 5 seconds
    time.sleep(5)
    
