import tushare as ts
import pandas as pd
import os
import time
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


start_date = '20151011'
base_dir = "stock_data/daily_factor"

def get_daily_factor(stock_code_list: List[str],start_data:str = '20150101',end_date: str = None)->int:
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    num = 0
    for stock_code in stock_code_list:
        # 判断base_dir目录是否存在，不存在则创建
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        
        # 构建输出文件路径
        output_file = os.path.join(base_dir, f"{stock_code}.csv")
        
        # 检查文件是否存在
        if os.path.exists(output_file):
            num += 1
            continue
        
        # 拉取数据
        df = common.pro.stk_factor(ts_code=stock_code, start_date=start_data, end_date=end_date)
        
        # 保存到CSV文件
        df.to_csv(output_file, index=False,encoding='utf-8-sig')
        num += 1
        # 打印进度
        print(f"已保存第 {num}/{len(stock_code_list)} 只股票 {stock_code} 的复权因子数据到 {output_file}")
        
        time.sleep(6.01)
    return num

if __name__ == "__main__":
    common.init_tushare()
    stock_code_list = common.get_all_stock_code()
    while True:
        num = get_daily_factor(stock_code_list)
        if num == len(stock_code_list):
            break
        else:
            time.sleep(60)
    
    
