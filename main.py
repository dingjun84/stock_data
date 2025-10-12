import tushare as ts
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
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
    data_dir = 'stock_data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"创建数据目录: {data_dir}")
    
    # 读取股票基础信息文件
    stock_basic_file = 'tushare_stock_basic_20251010230828.csv'
    print(f"正在读取股票基础信息: {stock_basic_file}")
    
    try:
        stock_basic_df = pd.read_csv(stock_basic_file, dtype={'list_date': str})
        print(f"成功读取 {len(stock_basic_df)} 只股票信息")
        
        # 统一的结束日期
        end_date = '20251010'
        
        # 限制处理数量（可根据需要调整）
        max_stocks = 1200  # 每次执行最多处理的股票数量
        
        print(f"开始处理数据，最多处理 {max_stocks} 只需要更新的股票...")
        
        success_count = 0
        skipped_count = 0
        failed_stocks = []
        processed_count = 0  # 实际处理的股票数量
        
        for index, row in stock_basic_df.iterrows():
            # 如果已经处理了足够数量的股票，就停止
            if processed_count >= max_stocks:
                print(f"\n已达到最大处理数量 ({max_stocks})，停止处理")
                break
            ts_code = row['ts_code']
            original_start_date = str(row['list_date'])  # 确保是字符串类型
            stock_name = row['name']
            
            print(f"\n检查 {index+1}: {ts_code} ({stock_name})")
            print(f"原始数据范围: {original_start_date} -> {end_date}")
            
            try:
                # 检查是否已有数据文件
                output_file = os.path.join(data_dir, f'stock_data_{ts_code.replace(".", "_")}.csv')
                existing_data = None
                actual_start_date = str(original_start_date)
                
                if os.path.exists(output_file):
                    print(f"  发现现有文件: {output_file}")
                    try:
                        existing_data = pd.read_csv(output_file, dtype={'trade_date': str})
                        
                        # 检查文件是否需要重新拉取
                        need_redownload = False
                        redownload_reason = ""
                        
                        if existing_data.empty:
                            need_redownload = True
                            redownload_reason = "文件为空"
                        else:
                            # 检查1: 开始日期是否是股票上市日期
                            earliest_date = str(existing_data['trade_date'].min())
                            if earliest_date != original_start_date:
                                need_redownload = True
                                redownload_reason = f"开始日期不匹配 (文件:{earliest_date}, 预期:{original_start_date})"
                            
                            # 检查2: 结束日期是否是给定的截止日期
                            if not need_redownload:
                                latest_date = str(existing_data['trade_date'].max())
                                if latest_date < end_date:
                                    # 如果最新日期小于截止日期，进行增量更新
                                    latest_dt = datetime.strptime(latest_date, '%Y%m%d')
                                    next_dt = latest_dt + timedelta(days=1)
                                    actual_start_date = next_dt.strftime('%Y%m%d')
                                    print(f"  现有数据最新日期: {latest_date}")
                                    print(f"  增量更新: 从 {actual_start_date} 开始拉取")
                                    
                                    # 标记开始处理
                                    processed_count += 1
                                    print(f"  开始处理 ({processed_count}/{max_stocks})")
                                else:
                                    # 数据已完整
                                    print(f"  数据已完整 ({len(existing_data)} 条记录)，跳过")
                                    print(f"  日期范围: {earliest_date} ~ {latest_date}")
                                    skipped_count += 1
                                    continue
                        
                        if need_redownload:
                            print(f"  需要重新拉取: {redownload_reason}")
                            print(f"  删除现有文件并重新拉取全部数据")
                            try:
                                os.remove(output_file)
                                print(f"  已删除文件: {output_file}")
                            except Exception as e:
                                print(f"  删除文件失败: {e}")
                            existing_data = None
                            # 标记开始处理
                            processed_count += 1
                            print(f"  开始处理 ({processed_count}/{max_stocks})")
                            
                    except Exception as e:
                        print(f"  读取现有文件失败: {e}，重新拉取全部数据")
                        existing_data = None
                        # 标记开始处理
                        processed_count += 1
                        print(f"  开始处理 ({processed_count}/{max_stocks})")
                else:
                    print(f"  新文件: {output_file}")
                    # 标记开始处理
                    processed_count += 1
                    print(f"  开始处理 ({processed_count}/{max_stocks})")
                
                # 分批拉取数据
                all_data = []
                current_start = str(actual_start_date)  # 使用实际开始日期
                batch_count = 0
                
                while current_start <= end_date:
                    batch_count += 1
                    print(f"  批次 {batch_count}: 拉取 {current_start} -> {end_date}")
                    
                    # 获取当前批次数据
                    df_batch = pro.daily(ts_code=ts_code, start_date=current_start, end_date=end_date)
                    
                    if df_batch.empty:
                        print(f"  批次 {batch_count}: 无数据")
                        break
                    
                    print(f"  批次 {batch_count}: 获取到 {len(df_batch)} 条记录")
                    all_data.append(df_batch)
                    
                    # 如果获取的数据少于6000条，说明已经是最后一批
                    if len(df_batch) < 6000:
                        print(f"  批次 {batch_count}: 数据拉取完成（最后一批）")
                        break
                    
                    # 计算下一批的开始日期（当前批最早日期的前一天）
                    # tushare返回的数据是按日期倒序排列的
                    earliest_date = str(df_batch['trade_date'].min())  # 确保是字符串
                    
                    # 将日期字符串转换为datetime，减1天，再转回字符串
                    earliest_dt = datetime.strptime(earliest_date, '%Y%m%d')
                    next_end_dt = earliest_dt - timedelta(days=1)
                    next_end_date = next_end_dt.strftime('%Y%m%d')
                    
                    # 如果计算的结束日期已经早于原始开始日期，退出循环
                    if next_end_date < str(current_start):
                        print(f"  已到达数据起始点，停止拉取")
                        break
                    
                    # 更新end_date为下一批的结束日期
                    end_date_for_next = next_end_date
                    print(f"  下一批将拉取: {current_start} -> {end_date_for_next}")
                    
                    # 添加延时避免API限制
                    time.sleep(0.5)
                    
                    # 如果下一批的结束日期早于开始日期，说明数据已全部获取
                    if end_date_for_next < str(current_start):
                        break
                    
                    # 为下一次循环准备
                    end_date = end_date_for_next
                
                # 合并所有批次的数据
                if all_data:
                    new_df = pd.concat(all_data, ignore_index=True)
                    
                    # 如果有现有数据，则合并
                    if existing_data is not None and not existing_data.empty:
                        print(f"  合并现有数据 ({len(existing_data)} 条) 与新数据 ({len(new_df)} 条)")
                        final_df = pd.concat([existing_data, new_df], ignore_index=True)
                        # 去除可能的重复数据
                        final_df = final_df.drop_duplicates(subset=['trade_date'], keep='last')
                    else:
                        final_df = new_df
                    
                    # 按日期排序（从早到晚）
                    final_df = final_df.sort_values('trade_date').reset_index(drop=True)
                    
                    # 导出到CSV文件
                    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    
                    if existing_data is not None and not existing_data.empty:
                        print(f"成功更新 {len(final_df)} 条记录到 {output_file} (新增{len(new_df)}条，共{batch_count}个批次)")
                    else:
                        print(f"成功导出 {len(final_df)} 条记录到 {output_file} (共{batch_count}个批次)")
                    success_count += 1
                elif existing_data is not None and not existing_data.empty:
                    # 如果没有新数据但有现有数据，表示数据已经是最新的
                    print(f"无新数据需要拉取，保持现有 {len(existing_data)} 条记录")
                    skipped_count += 1
                else:
                    print(f"警告: {ts_code} 没有获取到任何数据")
                    failed_stocks.append(ts_code)
                
                # 重置end_date为原始值，为下一只股票做准备
                end_date = '20251010'
                
            except Exception as e:
                print(f"错误: 处理 {ts_code} 时发生异常: {str(e)}")
                failed_stocks.append(ts_code)
                # 重置end_date
                end_date = '20251010'
        
        # 输出统计信息
        print(f"\n处理完成!")
        print(f"实际处理: {processed_count} 只股票 (限制: {max_stocks})")
        print(f"成功处理: {success_count} 只股票")
        if skipped_count > 0:
            print(f"跳过(已完整): {skipped_count} 只股票")
        if failed_stocks:
            print(f"失败股票: {failed_stocks}")
        
        total_checked = success_count + skipped_count + len(failed_stocks)
        print(f"总计检查: {total_checked} 只股票 (处理{processed_count} + 跳过{skipped_count})")
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {stock_basic_file}")
        print("请确保文件存在于当前目录中")
    except Exception as e:
        print(f"发生错误: {str(e)}")

