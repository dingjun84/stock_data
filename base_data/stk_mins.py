import tushare as ts
import pandas as pd
import os
import time
from typing import List,Dict

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


start_date = '2020-01-01 09:00:00'
base_dir = "stock_data/fifteen"

def get_stk_mins(stock_listdate: Dict[str,str],start_data:str = start_date,end_date: str = None):
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    num = 0
    for stock_code,list_date in stock_listdate.items():
        # 转换为datetime对象
        list_date_dt = datetime.strptime(list_date, '%Y%m%d')
        # 如果list_date早于start_date，设置为start_date
        if list_date_dt > datetime.strptime(start_data, '%Y-%m-%d %H:%M:%S'):
            start_data = list_date_dt.strftime('%Y-%m-%d %H:%M:%S')

        # 按年拉取数据
        start_year = datetime.strptime(start_data, '%Y-%m-%d %H:%M:%S').year
        end_year = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S').year
        for year in range(start_year, end_year + 1):
            start_year_date = f"{year}-01-01 00:00:00"
            end_year_date = f"{year}-12-31 23:59:59"
            if start_year_date < start_data:
                start_year_date = start_data
            if end_year_date > end_date:
                end_year_date = end_date

            # 判断base_dir目录是否存在，不存在则创建
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            csv_file = os.path.join(base_dir, f"{stock_code}_{year}.csv")
            # 如果文件已存在，跳过
            if os.path.exists(csv_file):
                print(f"{stock_code} {year} 年数据已存在，跳过")
                continue
            df = common.pro.stk_mins(ts_code=stock_code, freq='15min',start_date=start_year_date,end_date=end_year_date)
            df.to_csv(csv_file, index=False,encoding='utf-8-sig')
            
            print(f"{stock_code} {year} 年数据已保存")
        num += 1
        print(f"共 {num}/{len(stock_listdate)} 只股票 15min数据已保存")
        # 10条数据休息一下
        if num % 2 == 0:
            time.sleep(1)

if __name__ == "__main__":
    common.init_tushare()
    stock_listdate = common.get_all_stock_listdate()
    get_stk_mins(stock_listdate)