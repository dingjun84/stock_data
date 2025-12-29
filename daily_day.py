import tushare as ts
import pandas as pd
import os
import time
import sys
from datetime import datetime, timedelta

# 按交易日期拉取所有股票数据
if __name__ == '__main__':
    # 检查是否为自动模式（由run.py调用）
    auto_mode = len(sys.argv) > 1 and sys.argv[1] == '--auto'
    # 从环境变量获取tushare token
    tushare_token = os.getenv('TUSHARE_TOKEN')
    
    if not tushare_token:
        print("错误: 未设置TUSHARE_TOKEN环境变量")
        print("请先设置环境变量：export TUSHARE_TOKEN='your_token_here'")
        print("或者运行: python3 set_token.py 来自动设置")
        exit(1)
    
    try:
        pro = ts.pro_api(tushare_token)
        print("Tushare API 初始化成功")
    except Exception as e:
        print(f"Tushare API 初始化失败: {e}")
        print("请检查TUSHARE_TOKEN是否正确")
        exit(1)

    # 创建数据目录
    data_dir = 'stock_data/daily'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"创建数据目录: {data_dir}")
    
    # 读取股票基础信息文件
    stock_basic_file = 'tushare_stock_basic_20251010230828.csv'
    print(f"正在读取股票基础信息: {stock_basic_file}")
    
    try:
        stock_basic_df = pd.read_csv(stock_basic_file, dtype={'list_date': str})
        print(f"成功读取 {len(stock_basic_df)} 只股票信息")
        
        # 创建股票代码到名称的映射
        stock_name_map = dict(zip(stock_basic_df['ts_code'], stock_basic_df['name']))
        stock_list_date_map = dict(zip(stock_basic_df['ts_code'], stock_basic_df['list_date']))
        
        # 自动读取现有数据文件中的最新日期
        print(f"\n正在扫描现有数据文件...")
        latest_date_in_files = None
        csv_files = [f for f in os.listdir(data_dir) if f.startswith('stock_data_') and f.endswith('.csv')]
        
        if csv_files:
            print(f"找到 {len(csv_files)} 个数据文件，正在查找最新日期...")
            max_dates = []
            for csv_file in csv_files:
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
                print(f"现有数据文件中的最新日期: {latest_date_in_files}")
                # 计算下一天作为起始日期
                latest_dt = datetime.strptime(latest_date_in_files, '%Y%m%d')
                next_dt = latest_dt + timedelta(days=1)
                start_date = next_dt.strftime('%Y%m%d')
            else:
                print(f"未能从现有文件中读取到有效日期，使用默认起始日期")
                start_date = '20151011'
        else:
            print(f"未找到现有数据文件，使用默认起始日期")
            start_date = '20151011'
        
        # 获取当前日期
        today = datetime.now().strftime('%Y%m%d')
        
        # 让用户输入要拉取的日期
        print(f"\n=== 按交易日期拉取股票数据 ===")
        if latest_date_in_files:
            print(f"数据文件最新日期: {latest_date_in_files}")
        print(f"建议起始日期: {start_date} (下一个待拉取日期)")
        print(f"当前日期: {today}")
        
        # 计算需要补充的天数
        if start_date <= today:
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            today_dt = datetime.strptime(today, '%Y%m%d')
            days_to_fetch = (today_dt - start_dt).days + 1
            print(f"需要补充的天数: {days_to_fetch} 天 (从 {start_date} 到 {today})")
        else:
            print(f"注意: 数据已是最新，无需补充")
        
        # 自动模式直接使用模式2
        if auto_mode:
            print(f"\n✓ 自动模式: 将从 {start_date} 逐天拉取到 {today}")
            mode = "2"
        else:
            print(f"\n可选模式:")
            print(f"1. 拉取单个交易日")
            print(f"2. 从指定日期开始每天拉取（需要多次执行）")
            mode = input("\n请选择模式 (1/2, 默认1): ").strip() or "1"
        
        if mode == "1":
            # 单日模式
            trade_date_input = input(f"请输入要拉取的交易日期 (格式: YYYYMMDD, 默认: {start_date}): ").strip()
            if not trade_date_input:
                trade_date = start_date
            else:
                trade_date = trade_date_input
            
            print(f"\n开始拉取 {trade_date} 的所有股票数据...")
            
            try:
                # 使用 trade_date 参数拉取当天所有股票的数据
                print(f"正在调用 API: pro.daily(trade_date='{trade_date}')")
                df_daily = pro.daily(trade_date=trade_date)
                
                if df_daily.empty:
                    print(f"警告: {trade_date} 没有交易数据（可能是非交易日）")
                    exit(0)
                
                print(f"成功获取 {len(df_daily)} 条记录（{len(df_daily['ts_code'].unique())} 只股票）")
                
                # 按股票代码分组处理
                success_count = 0
                update_count = 0
                new_count = 0
                failed_stocks = []
                
                for ts_code, group_df in df_daily.groupby('ts_code'):
                    try:
                        stock_name = stock_name_map.get(ts_code, '未知')
                        list_date = stock_list_date_map.get(ts_code, 'N/A')
                        
                        # 检查该股票是否在这个日期之前上市
                        if list_date != 'N/A' and list_date > trade_date:
                            print(f"  跳过 {ts_code} ({stock_name}): 上市日期 {list_date} 晚于交易日期 {trade_date}")
                            continue
                        
                        output_file = os.path.join(data_dir, f'stock_data_{ts_code.replace(".", "_")}.csv')
                        
                        # 检查文件是否存在
                        if os.path.exists(output_file):
                            # 读取现有数据
                            existing_data = pd.read_csv(output_file, dtype={'trade_date': str})
                            
                            # 检查是否已有该日期的数据
                            if trade_date in existing_data['trade_date'].values:
                                # 更新数据（删除旧的，添加新的）
                                existing_data = existing_data[existing_data['trade_date'] != trade_date]
                                final_df = pd.concat([existing_data, group_df], ignore_index=True)
                                print(f"  更新 {ts_code} ({stock_name}): 替换 {trade_date} 的数据")
                                update_count += 1
                            else:
                                # 追加新数据
                                final_df = pd.concat([existing_data, group_df], ignore_index=True)
                                print(f"  追加 {ts_code} ({stock_name}): 新增 {trade_date} 的数据")
                                new_count += 1
                            
                            # 按日期排序
                            final_df = final_df.sort_values('trade_date').reset_index(drop=True)
                            final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                        else:
                            # 新文件
                            group_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                            print(f"  新建 {ts_code} ({stock_name}): 创建文件并写入 {trade_date} 的数据")
                            new_count += 1
                        
                        success_count += 1
                        
                    except Exception as e:
                        print(f"  错误: 处理 {ts_code} 时发生异常: {str(e)}")
                        failed_stocks.append(ts_code)
                
                # 输出统计信息
                print(f"\n处理完成!")
                print(f"交易日期: {trade_date}")
                print(f"成功处理: {success_count} 只股票")
                print(f"  - 新建文件: {new_count} 只")
                print(f"  - 追加数据: {new_count} 只")
                print(f"  - 更新数据: {update_count} 只")
                if failed_stocks:
                    print(f"失败股票: {failed_stocks}")
                    
            except Exception as e:
                print(f"拉取数据失败: {str(e)}")
                exit(1)
                
        else:
            # 连续拉取模式
            progress_file = 'progress_daily.txt'
            
            if auto_mode:
                # 自动模式：循环拉取直到今天
                print(f"\n自动模式：将循环拉取所有缺失日期")
                trade_date = start_date
                total_days_processed = 0
                total_success = 0
            else:
                # 手动模式：每次只拉一天
                print(f"\n注意: 每次执行只拉取一个交易日的数据")
                print(f"系统会记录进度，下次执行时继续下一个交易日")
                
                # 读取或创建进度文件
                if os.path.exists(progress_file):
                    with open(progress_file, 'r') as f:
                        current_date = f.read().strip()
                    print(f"从进度文件读取到上次拉取日期: {current_date}")
                    # 计算下一个日期（自然日）
                    current_dt = datetime.strptime(current_date, '%Y%m%d')
                    next_dt = current_dt + timedelta(days=1)
                    trade_date = next_dt.strftime('%Y%m%d')
                else:
                    trade_date = start_date
                
                print(f"\n本次将拉取: {trade_date}")
                confirm = input("是否继续? (y/n, 默认y): ").strip().lower()
                if confirm and confirm != 'y':
                    print("取消执行")
                    exit(0)
            
            # 循环处理
            while True:
                try:
                    # 使用 trade_date 参数拉取当天所有股票的数据
                    print(f"\n正在调用 API: pro.daily(trade_date='{trade_date}')")
                    df_daily = pro.daily(trade_date=trade_date)
                    
                    if df_daily.empty:
                        print(f"  提示: {trade_date} 没有交易数据（可能是非交易日）")
                        # 自动模式继续下一天，手动模式保存进度并退出
                        if auto_mode:
                            total_days_processed += 1
                            # 继续下一天
                            current_dt = datetime.strptime(trade_date, '%Y%m%d')
                            next_dt = current_dt + timedelta(days=1)
                            trade_date = next_dt.strftime('%Y%m%d')
                            
                            if trade_date <= today:
                                continue
                            else:
                                print(f"\n{'='*60}")
                                print(f"自动模式完成!")
                                print(f"  扫描天数: {total_days_processed} 天")
                                print(f"  累计处理: {total_success} 只股票次")
                                print(f"{'='*60}")
                                break
                        else:
                            # 仍然保存进度，继续下一个日期
                            with open(progress_file, 'w') as f:
                                f.write(trade_date)
                            print(f"  已保存进度，下次执行将拉取下一个日期")
                            exit(0)
                    
                    print(f"  成功获取 {len(df_daily)} 条记录（{len(df_daily['ts_code'].unique())} 只股票）")
                    
                    # 按股票代码分组处理
                    success_count = 0
                    update_count = 0
                    new_count = 0
                    failed_stocks = []
                    
                    for ts_code, group_df in df_daily.groupby('ts_code'):
                        try:
                            stock_name = stock_name_map.get(ts_code, '未知')
                            list_date = stock_list_date_map.get(ts_code, 'N/A')
                            
                            # 检查该股票是否在这个日期之前上市
                            if list_date != 'N/A' and list_date > trade_date:
                                continue
                            
                            output_file = os.path.join(data_dir, f'stock_data_{ts_code.replace(".", "_")}.csv')
                            
                            # 检查文件是否存在
                            if os.path.exists(output_file):
                                # 读取现有数据
                                existing_data = pd.read_csv(output_file, dtype={'trade_date': str})
                                
                                # 检查是否已有该日期的数据
                                if trade_date in existing_data['trade_date'].values:
                                    # 更新数据
                                    existing_data = existing_data[existing_data['trade_date'] != trade_date]
                                    final_df = pd.concat([existing_data, group_df], ignore_index=True)
                                    update_count += 1
                                else:
                                    # 追加新数据
                                    final_df = pd.concat([existing_data, group_df], ignore_index=True)
                                    new_count += 1
                                
                                # 按日期排序
                                final_df = final_df.sort_values('trade_date').reset_index(drop=True)
                                final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                            else:
                                # 新文件
                                group_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                                new_count += 1
                            
                            success_count += 1
                            
                        except Exception as e:
                            print(f"  错误: 处理 {ts_code} 时发生异常: {str(e)}")
                            failed_stocks.append(ts_code)
                    
                    # 输出统计信息
                    print(f"  ✓ {trade_date}: 成功处理 {success_count} 只股票 (新增/追加:{new_count}, 更新:{update_count})")
                    if failed_stocks and len(failed_stocks) <= 5:
                        print(f"    失败: {failed_stocks}")
                    
                    # 自动模式继续下一天，手动模式保存进度并退出
                    if auto_mode:
                        total_days_processed += 1
                        total_success += success_count
                        
                        # 继续下一天
                        current_dt = datetime.strptime(trade_date, '%Y%m%d')
                        next_dt = current_dt + timedelta(days=1)
                        trade_date = next_dt.strftime('%Y%m%d')
                        
                        if trade_date <= today:
                            time.sleep(0.3)  # API限流
                            continue
                        else:
                            # 所有日期都处理完了
                            print(f"\n{'='*60}")
                            print(f"自动模式完成!")
                            print(f"  处理天数: {total_days_processed} 天")
                            print(f"  累计处理: {total_success} 只股票次")
                            print(f"{'='*60}")
                            break
                    else:
                        # 保存进度
                        with open(progress_file, 'w') as f:
                            f.write(trade_date)
                        
                        print(f"\n处理完成!")
                        print(f"交易日期: {trade_date}")
                        print(f"成功处理: {success_count} 只股票")
                        print(f"  - 新建/追加: {new_count} 只")
                        print(f"  - 更新数据: {update_count} 只")
                        if failed_stocks:
                            print(f"失败股票: {failed_stocks}")
                        print(f"\n已保存进度到 {progress_file}")
                        print(f"下次执行将继续拉取下一个日期")
                        break
                        
                except Exception as e:
                    print(f"拉取数据失败: {str(e)}")
                    if auto_mode:
                        print(f"  跳过日期 {trade_date}，继续下一天")
                        total_days_processed += 1
                        current_dt = datetime.strptime(trade_date, '%Y%m%d')
                        next_dt = current_dt + timedelta(days=1)
                        trade_date = next_dt.strftime('%Y%m%d')
                        if trade_date <= today:
                            continue
                        else:
                            break
                    else:
                        exit(1)
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {stock_basic_file}")
        print("请确保文件存在于当前目录中")
    except Exception as e:
        print(f"发生错误: {str(e)}")

