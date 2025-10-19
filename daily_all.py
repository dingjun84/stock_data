import tushare as ts
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# 按交易日期拉取所有股票数据（当天）
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
        
        # 使用执行脚本的当天日期
        trade_date = datetime.now().strftime('%Y%m%d')
        
        print(f"\n=== 按交易日期拉取股票数据 ===")
        print(f"交易日期: {trade_date} (今天)")
        print(f"\n开始拉取 {trade_date} 的所有股票数据...")
        
        try:
            # 使用 trade_date 参数拉取当天所有股票的数据
            print(f"正在调用 API: pro.daily(trade_date='{trade_date}')")
            df_daily = pro.daily(trade_date=trade_date)
            
            if df_daily.empty:
                print(f"提示: {trade_date} 没有交易数据（可能是非交易日或数据尚未更新）")
                exit(0)
            
            print(f"成功获取 {len(df_daily)} 条记录（{len(df_daily['ts_code'].unique())} 只股票）")
            
            # 按股票代码分组处理
            success_count = 0
            update_count = 0
            new_count = 0
            append_count = 0
            skipped_count = 0
            failed_stocks = []
            
            total_stocks = len(df_daily['ts_code'].unique())
            current_index = 0
            
            for ts_code, group_df in df_daily.groupby('ts_code'):
                current_index += 1
                try:
                    stock_name = stock_name_map.get(ts_code, '未知')
                    list_date = stock_list_date_map.get(ts_code, 'N/A')
                    
                    # 检查该股票是否在这个日期之前上市
                    if list_date != 'N/A' and list_date > trade_date:
                        print(f"  [{current_index}/{total_stocks}] 跳过 {ts_code} ({stock_name}): 上市日期 {list_date} 晚于交易日期 {trade_date}")
                        skipped_count += 1
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
                            print(f"  [{current_index}/{total_stocks}] 更新 {ts_code} ({stock_name}): 替换 {trade_date} 的数据")
                            update_count += 1
                        else:
                            # 追加新数据
                            final_df = pd.concat([existing_data, group_df], ignore_index=True)
                            print(f"  [{current_index}/{total_stocks}] 追加 {ts_code} ({stock_name}): 新增 {trade_date} 的数据")
                            append_count += 1
                        
                        # 按日期排序
                        final_df = final_df.sort_values('trade_date').reset_index(drop=True)
                        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    else:
                        # 新文件
                        group_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                        print(f"  [{current_index}/{total_stocks}] 新建 {ts_code} ({stock_name}): 创建文件并写入 {trade_date} 的数据")
                        new_count += 1
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"  [{current_index}/{total_stocks}] 错误: 处理 {ts_code} 时发生异常: {str(e)}")
                    failed_stocks.append(ts_code)
            
            # 输出统计信息
            print(f"\n{'='*60}")
            print(f"处理完成!")
            print(f"{'='*60}")
            print(f"交易日期: {trade_date}")
            print(f"API返回股票数: {total_stocks} 只")
            print(f"成功处理: {success_count} 只股票")
            print(f"  - 新建文件: {new_count} 只")
            print(f"  - 追加数据: {append_count} 只")
            print(f"  - 更新数据: {update_count} 只")
            if skipped_count > 0:
                print(f"  - 跳过(未上市): {skipped_count} 只")
            if failed_stocks:
                print(f"失败股票 ({len(failed_stocks)}只): {failed_stocks}")
            print(f"{'='*60}")
                
        except Exception as e:
            print(f"拉取数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            exit(1)
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {stock_basic_file}")
        print("请确保文件存在于当前目录中")
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
