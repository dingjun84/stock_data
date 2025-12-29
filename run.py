#!/usr/bin/env python3
"""
股票数据获取程序启动器 - 全自动模式
1. 检查所有股票，为没有数据的股票拉取历史数据（到20251010）
2. 调用 daily_day.py 按天补齐数据直到执行当天
"""
import os
import sys
import subprocess
import pandas as pd
from datetime import datetime, timedelta
import tushare as ts
import time

def load_env_file():
    """从.env文件加载环境变量"""
    env_file = '.env'
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            return True
        except Exception as e:
            print(f"读取.env文件失败: {e}")
            return False
    return False

def check_token():
    """检查TUSHARE_TOKEN是否已设置"""
    # 先从.env文件加载
    load_env_file()
    
    token = os.getenv('TUSHARE_TOKEN')
    if token and len(token) > 10:  # 基本验证
        return True
    return False

def fetch_stock_history(pro, ts_code, stock_name, start_date, end_date, output_file):
    """拉取单只股票的历史数据"""
    try:
        print(f"    正在拉取 {ts_code} ({stock_name}) 从 {start_date} 到 {end_date}")
        
        all_data = []
        current_end = end_date
        batch_count = 0
        
        while True:
            batch_count += 1
            df_batch = pro.daily(ts_code=ts_code, start_date=start_date, end_date=current_end)
            
            if df_batch.empty:
                break
            
            all_data.append(df_batch)
            
            # 如果获取的数据少于6000条，说明已经是最后一批
            if len(df_batch) < 6000:
                break
            
            # 计算下一批的结束日期（当前批最早日期的前一天）
            earliest_date = str(df_batch['trade_date'].min())
            earliest_dt = datetime.strptime(earliest_date, '%Y%m%d')
            next_end_dt = earliest_dt - timedelta(days=1)
            next_end_date = next_end_dt.strftime('%Y%m%d')
            
            # 如果计算的结束日期已经早于原始开始日期，退出循环
            if next_end_date < start_date:
                break
            
            current_end = next_end_date
            time.sleep(0.3)  # 添加延时避免API限制
        
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            final_df = final_df.sort_values('trade_date').reset_index(drop=True)
            final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"    ✓ 成功拉取 {len(final_df)} 条记录 (共{batch_count}个批次)")
            return True
        else:
            print(f"    ✗ 未获取到数据")
            return False
            
    except Exception as e:
        print(f"    ✗ 拉取失败: {str(e)}")
        return False

def check_and_fetch_missing_stocks():
    """检查并拉取缺失的股票数据"""
    print("\n" + "="*60)
    print("步骤 1: 检查并拉取缺失的股票历史数据")
    print("="*60)
    
    # 获取token
    tushare_token = os.getenv('TUSHARE_TOKEN')
    if not tushare_token:
        print("错误: 未设置TUSHARE_TOKEN环境变量")
        return False
    
    try:
        pro = ts.pro_api(tushare_token)
        print("✓ Tushare API 初始化成功")
    except Exception as e:
        print(f"✗ Tushare API 初始化失败: {e}")
        return False
    
    # 创建数据目录
    data_dir = 'stock_data/daily'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"✓ 创建数据目录: {data_dir}")
    
    # 读取股票基础信息
    stock_basic_file = 'tushare_stock_basic_20251010230828.csv'
    try:
        stock_basic_df = pd.read_csv(stock_basic_file, dtype={'list_date': str})
        print(f"✓ 读取 {len(stock_basic_df)} 只股票信息")
    except Exception as e:
        print(f"✗ 读取股票信息失败: {e}")
        return False
    
    # 动态获取现有数据的最新日期作为截止日期
    print(f"\n正在检测现有数据的最新日期...")
    latest_date_in_files = None
    csv_files = [f for f in os.listdir(data_dir) if f.startswith('stock_data_') and f.endswith('.csv')]
    
    if csv_files:
        print(f"找到 {len(csv_files)} 个现有数据文件，正在查找最新日期...")
        max_dates = []
        for csv_file in csv_files[:100]:  # 采样100个文件即可
            try:
                file_path = os.path.join(data_dir, csv_file)
                df_temp = pd.read_csv(file_path, dtype={'trade_date': str})
                if not df_temp.empty and 'trade_date' in df_temp.columns:
                    max_date = df_temp['trade_date'].max()
                    max_dates.append(max_date)
            except Exception as e:
                continue
        
        if max_dates:
            latest_date_in_files = max(max_dates)
            end_date = latest_date_in_files
            print(f"✓ 检测到现有数据最新日期: {end_date}")
        else:
            end_date = '20251227'
            print(f"未能检测到有效日期，使用默认截止日期: {end_date}")
    else:
        end_date = '20251227'
        print(f"未找到现有数据文件，使用默认截止日期: {end_date}")
    
    print(f"新股票将拉取数据到: {end_date}")
    
    # 检查每只股票
    missing_stocks = []
    empty_stocks = []
    valid_stocks = 0
    
    print(f"\n正在扫描股票数据文件...")
    for index, row in stock_basic_df.iterrows():
        ts_code = row['ts_code']
        output_file = os.path.join(data_dir, f'stock_data_{ts_code.replace(".", "_")}.csv')
        
        if not os.path.exists(output_file):
            missing_stocks.append((ts_code, row['name'], row['list_date']))
        else:
            try:
                df = pd.read_csv(output_file, dtype={'trade_date': str})
                if df.empty:
                    empty_stocks.append((ts_code, row['name'], row['list_date']))
                else:
                    valid_stocks += 1
            except Exception as e:
                empty_stocks.append((ts_code, row['name'], row['list_date']))
    
    total_to_fetch = len(missing_stocks) + len(empty_stocks)
    
    print(f"\n扫描结果:")
    print(f"  - 已有有效数据: {valid_stocks} 只股票")
    print(f"  - 缺失数据文件: {len(missing_stocks)} 只股票")
    print(f"  - 数据文件为空: {len(empty_stocks)} 只股票")
    print(f"  - 需要拉取数据: {total_to_fetch} 只股票")
    print(f"  - 拉取截止日期: {end_date} (与现有数据保持一致)")
    
    if total_to_fetch == 0:
        print(f"\n✓ 所有股票都已有历史数据（到 {end_date}）")
        return True
    
    # 询问是否继续
    print(f"\n准备拉取 {total_to_fetch} 只股票的历史数据")
    print(f"拉取范围: 从上市日期到 {end_date}")
    confirm = input("是否继续? (y/n, 默认y): ").strip().lower()
    if confirm and confirm != 'y':
        print("取消执行")
        return False
    
    # 拉取缺失的数据
    success_count = 0
    failed_stocks = []
    
    stocks_to_fetch = missing_stocks + empty_stocks
    
    print(f"\n开始拉取数据...")
    for i, (ts_code, stock_name, list_date) in enumerate(stocks_to_fetch, 1):
        print(f"\n[{i}/{total_to_fetch}] {ts_code} ({stock_name})")
        output_file = os.path.join(data_dir, f'stock_data_{ts_code.replace(".", "_")}.csv')
        
        # 删除空文件
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass
        
        # 拉取数据
        if list_date <= "20151011":
            list_date = "20151011"
        if fetch_stock_history(pro, ts_code, stock_name, list_date, end_date, output_file):
            success_count += 1
        else:
            failed_stocks.append(ts_code)
        
        # 每10只股票暂停一下
        if i % 10 == 0:
            time.sleep(1)
    
    # 输出统计
    print(f"\n" + "="*60)
    print(f"步骤 1 完成!")
    print(f"  - 成功拉取: {success_count}/{total_to_fetch} 只股票")
    if failed_stocks:
        print(f"  - 失败: {len(failed_stocks)} 只")
        print(f"    {failed_stocks[:10]}" + ("..." if len(failed_stocks) > 10 else ""))
    print("="*60)
    
    return True

def run_daily_fill():
    """运行 daily_day.py 补齐数据"""
    print("\n" + "="*60)
    print("步骤 2: 按天补齐数据（从最新日期+1到今天）")
    print("="*60)
    
    try:
        # 使用 --auto 参数调用 daily_day.py，启用自动模式
        result = subprocess.run([sys.executable, 'daily_day.py', '--auto'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ daily_day.py 执行失败: {e}")
        return False
    except FileNotFoundError:
        print("✗ 找不到 daily_day.py 文件")
        return False

def main():
    print("="*60)
    print("股票数据获取程序 - 全自动模式")
    print("="*60)
    
    # 检查token
    if not check_token():
        print("\n未检测到TUSHARE_TOKEN环境变量")
        print("正在启动token设置工具...")
        
        # 运行token设置工具
        try:
            result = subprocess.run([sys.executable, 'set_token.py'], check=True)
        except subprocess.CalledProcessError:
            print("Token设置失败，程序退出")
            sys.exit(1)
        except FileNotFoundError:
            print("错误: 找不到set_token.py文件")
            sys.exit(1)
        
        # 重新检查token
        if not check_token():
            print("Token设置后仍然无效，程序退出")
            sys.exit(1)
    
    print("✓ TUSHARE_TOKEN 已配置\n")
    
    # 显示执行计划
    print("执行计划:")
    print("  1. 检测现有股票数据的最新日期")
    print("  2. 对于没有数据或数据为空的股票，拉取历史数据（到现有数据的最新日期）")
    print("  3. 调用 daily_day.py 按天补齐数据（从最新日期+1到今天）")
    print()
    
    # 步骤1: 检查并拉取缺失的股票数据
    if not check_and_fetch_missing_stocks():
        print("\n程序执行失败")
        sys.exit(1)
    
    # 步骤2: 运行 daily_day.py 补齐数据
    if not run_daily_fill():
        print("\n程序执行失败")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✓ 全部完成！所有股票数据已更新到最新")
    print("="*60)

if __name__ == '__main__':
    main()
