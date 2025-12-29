import tushare as ts
import pandas as pd
import os
from typing import List,Dict

from datetime import datetime, timedelta
import set_token
pro = None

def init_tushare():
    set_token.load_from_env()
    tushare_token = os.getenv('TUSHARE_TOKEN')
    
    if not tushare_token:
        print("错误: 未设置TUSHARE_TOKEN环境变量")
        print("请先设置环境变量：export TUSHARE_TOKEN='your_token_here'")
        print("或者运行: python3 set_token.py 来自动设置")
        exit(1)
    
    try:
        global pro
        pro = ts.pro_api(tushare_token)
        print("Tushare API 初始化成功")
    except Exception as e:
        print(f"Tushare API 初始化失败: {e}")
        print("请检查TUSHARE_TOKEN是否正确")
        exit(1)


def get_all_stock_code()->List[str]:
    # 读取股票基础信息文件
    stock_basic_file = 'tushare_stock_basic.csv'
    print(f"正在读取股票基础信息: {stock_basic_file}")
    
    
    stock_basic_df = pd.read_csv(stock_basic_file, dtype={'list_date': str})
        
    stock_code_list = stock_basic_df['ts_code'].tolist()
    print(f"成功读取 {len(stock_code_list)} 只股票信息")
    return stock_code_list

def get_all_stock_listdate()->Dict[str,str]:
    # 读取股票基础信息文件
    stock_basic_file = 'tushare_stock_basic.csv'
    print(f"正在读取股票基础信息: {stock_basic_file}")
    
    
    stock_basic_df = pd.read_csv(stock_basic_file, dtype={'list_date': str})
        
    stock_list_date_map = dict(zip(stock_basic_df['ts_code'], stock_basic_df['list_date']))
    print(f"成功读取 {len(stock_list_date_map)} 只股票信息")
    return stock_list_date_map
        