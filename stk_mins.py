import tushare as ts
import os

if __name__ == '__main__':
    pro = ts.pro_api("fe434a4dd73d5a0317bec4c3b075a767aec628af6333934414c1864b")

    #获取浦发银行60000.SH的历史分钟数据
    df = pro.stk_mins(ts_code='600000.SH', start_date='2025-10-14 09:00:00', end_date='2025-10-14 19:00:00')
    print(df)