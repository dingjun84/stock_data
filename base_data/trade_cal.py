import tushare as ts
import pandas as pd
import os

import sys
from datetime import datetime, timedelta

# 1. 获取当前脚本（run.py）的绝对路径
current_script_path = os.path.abspath(__file__)
# 2. 获取当前脚本所在目录（child目录）的绝对路径
current_dir = os.path.dirname(current_script_path)
# 3. 获取父级目录（parent目录）的绝对路径
parent_dir = os.path.dirname(current_dir)
# 4. 将父级目录添加到sys.path中（关键步骤）
if parent_dir not in sys.path:  # 避免重复添加
    sys.path.insert(0, parent_dir)  # 插入到列表头部，优先查找
import common


start_date = '20151011'
base_dir = "stock_data/trade_cal"


def get_trade_cal(end_date: str = None):
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    for exchange in ['SSE', 'SZSE']:
        df = common.pro.trade_cal(exchange=exchange, start_date=start_date, end_date=end_date)
        # 判断base_dir目录是否存在，不存在则创建
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        csv_file = os.path.join(base_dir, f"{exchange}_{start_date}_{end_date}.csv")
        df.to_csv(csv_file, index=False,encoding='utf-8-sig')
        print(f"已保存 {exchange} 交易日历到 {csv_file}")

if __name__ == "__main__":
    common.init_tushare()
    get_trade_cal()