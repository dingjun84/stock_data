import backtrader as bt
import sys
import os 
sys.path.append('.')
from strategy import hit_limitup_more_volume_double ,test_strategy


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
    # 遍历stock_datas/daily下的文件
    # ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount
    import pandas as pd
    i = 0
    for file in os.listdir('stock_datas/daily'):
        if i > 1:
            break

        if file.endswith('.csv'):
            df = pd.read_csv(f'stock_datas/daily/{file}', parse_dates=True)
            df = tushare2backtrader(df)
            data = bt.feeds.PandasData(dataname=df)
            cerebro = bt.Cerebro()
            cerebro.addstrategy(test_strategy.TestStrategy)
            cerebro.adddata(data)
            cerebro.broker.set_cash(1000000)
            cerebro.run()
            i += 1
            print(f'{file} done')   
