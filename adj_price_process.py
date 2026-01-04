import os
import pandas as pd
import glob


def adjust_price(adj_type='hfq'):
    """
    处理股票复权
    :param adj_type: 复权类型，'hfq'为后复权，'qfq'为前复权
    """
    # 定义常量
    PRICE_COLS = ['open', 'high', 'low', 'close', 'pre_close']
    FORMAT = lambda x: '%.2f' % x
    
    # 数据目录
    daily_dir = './stock_data/daily'
    factor_dir = './stock_data/factor'
    output_dir = './stock_data/adj_daily'
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有股票代码
    daily_files = glob.glob(os.path.join(daily_dir, 'stock_data_*.csv'))
    print(f"找到 {len(daily_files)} 个股票数据文件")
    
    # 遍历处理每个股票
    processed_count = 0
    for daily_file in daily_files:
        # 提取股票代码
        stock_code = os.path.basename(daily_file).replace('stock_data_', '').replace('.csv', '')
        # 将下划线替换为点号，以匹配复权因子文件名格式
        stock_code = stock_code.replace('_', '.')
        
        # 复权因子文件路径
        factor_file = os.path.join(factor_dir, f'{stock_code}.csv')
        
        # 检查复权因子文件是否存在
        if not os.path.exists(factor_file):
            print(f"跳过 {stock_code}: 复权因子文件不存在")
            continue
        
        try:
            # 读取股票数据
            stock_df = pd.read_csv(daily_file)
            
            # 读取复权因子数据
            factor_df = pd.read_csv(factor_file)
            
            # 确保日期列格式正确
            stock_df['trade_date'] = stock_df['trade_date'].astype(str)
            factor_df['trade_date'] = factor_df['trade_date'].astype(str)
            
            # 按trade_date合并数据
            merged_df = pd.merge(stock_df, factor_df[['trade_date', 'adj_factor']], 
                               on='trade_date', how='left')
            
            # 检查是否有缺失的复权因子
            if merged_df['adj_factor'].isnull().any():
                print(f"{stock_code}: 存在缺失的复权因子，将跳过")
                continue
            
            # 获取第一个复权因子（用于前复权计算）
            first_adj_factor = merged_df['adj_factor'].iloc[0]
            
            # 计算复权价格
            for col in PRICE_COLS:
                if adj_type == 'hfq':
                    # 后复权：价格 * 复权因子
                    merged_df[col] = merged_df[col] * merged_df['adj_factor']
                else:
                    # 前复权：价格 * 复权因子 / 第一个复权因子
                    merged_df[col] = merged_df[col] * merged_df['adj_factor'] / first_adj_factor
                
                # 格式化价格
                merged_df[col] = merged_df[col].map(FORMAT)
            
            # 将价格列转换为float类型
            for col in PRICE_COLS:
                merged_df[col] = merged_df[col].astype(float)
            
            # 计算复权后的涨跌幅
            merged_df['change'] = merged_df['close'] - merged_df['pre_close']
            merged_df['pct_chg'] = (merged_df['change'] / merged_df['pre_close']) * 100
            
            # 保存处理后的数据
            output_file = os.path.join(output_dir, f'stock_data_{stock_code}_{adj_type}.csv')
            merged_df.to_csv(output_file, index=False)
            
            processed_count += 1
            if processed_count % 100 == 0:
                print(f"已处理 {processed_count} 个股票")
                
        except Exception as e:
            print(f"处理 {stock_code} 时出错: {e}")
            continue
    
    print(f"复权处理完成，共处理 {processed_count} 个股票")
    print(f"复权数据保存到: {output_dir}")


if __name__ == "__main__":
    # 支持后复权和前复权
    adjust_price(adj_type='hfq')  # 处理后复权
    adjust_price(adj_type='qfq')  # 处理前复权
