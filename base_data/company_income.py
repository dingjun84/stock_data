import tushare as ts
import pandas as pd
import os
from typing import List

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

base_dir = "stock_data/company_income"
# 拉取所有股票的财务数据
def get_company_income(stock_code_list: List[str],start_data:str = '20150101',end_date: str = None):
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    num = 0
    for stock_code in stock_code_list:
        # 判断base_dir目录是否存在，不存在则创建
        if not os.path.exists(os.path.join(base_dir,end_date)):
            os.makedirs(os.path.join(base_dir,end_date))
        csv_file = os.path.join(base_dir,end_date, f"{stock_code}.csv")
        # 如果文件已存在，跳过
        if os.path.exists(csv_file):
            num += 1
            print(f"{stock_code} 财务数据已存在，跳过")
            continue
        df = common.pro.income(ts_code=stock_code,start_date=start_data,end_date=end_date)
        df.to_csv(csv_file, index=False,encoding='utf-8-sig')
        num += 1
        print(f"已保存第 {num}/{len(stock_code_list)} 只股票 {stock_code} 财务数据到 {csv_file}")
        # 10条数据休息一下
        if num % 10 == 0:
            time.sleep(1)

if __name__ == "__main__":
    common.init_tushare()
    stock_code_list = common.get_all_stock_code()
    get_company_income(stock_code_list)