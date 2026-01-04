import pandas as pd
import numpy as np
import os
import glob


def compute_features_single_stock(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算单只股票的时间序列特征
    :param df: 单只股票数据，按 trade_date 升序
    :return: 包含特征的DataFrame
    """
    df = df.copy()

    # === 统一稳健价格 ===
    df['P'] = (df['high'] + df['low'] + df['close']) / 3.0

    # === 动量 ===
    df['mom_5']    = df['P'] / df['P'].shift(5)  - 1
    df['mom_10']   = df['P'] / df['P'].shift(10) - 1
    df['mom_20']   = df['P'] / df['P'].shift(20) - 1
    df['mom_20_5'] = df['P'].shift(5) / df['P'].shift(25) - 1

    # === 均线 / 趋势 ===
    for n in (5, 10, 20):
        df[f'ma_{n}'] = df['P'].rolling(n).mean()
        df[f'trend_{n}'] = (df['P'] - df[f'ma_{n}']) / df[f'ma_{n}']

    df['ma_ratio_5_20']  = df['ma_5'] / df['ma_20']
    df['ma_ratio_10_20'] = df['ma_10'] / df['ma_20']

    # === 波动 / 区间 ===
    df['range_1'] = (df['high'] - df['low']) / df['P']
    df['range_5'] = df['range_1'].rolling(5).mean()
    df['range_20'] = df['range_1'].rolling(20).mean()
    df['range_ratio'] = df['range_5'] / df['range_20']

    # === K 线结构 ===
    df['body'] = (df['close'] - df['open']).abs() / df['P']
    df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['P']
    df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['P']
    df['shadow_ratio'] = df['upper_shadow'] / (df['lower_shadow'] + 1e-6)

    # === 成交量 / 成交额 ===
    df['vol_ma_5'] = df['vol'].rolling(5).mean()
    df['vol_ma_20'] = df['vol'].rolling(20).mean()
    df['vol_ratio_5'] = df['vol'] / df['vol_ma_5']
    df['vol_ratio_20'] = df['vol'] / df['vol_ma_20']

    df['amount_ma_5'] = df['amount'].rolling(5).mean()
    df['amount_ma_20'] = df['amount'].rolling(20).mean()
    df['amount_ratio'] = df['amount_ma_5'] / df['amount_ma_20']

    # === 量价关系 ===
    df['vol_price_corr_10'] = (
        np.log(df['P']).rolling(10).corr(np.log(df['vol']))
    )
    df['vol_price_corr_20'] = (
        np.log(df['P']).rolling(20).corr(np.log(df['vol']))
    )

    df['vol_mom_5'] = np.sign(df['mom_5']) * df['vol_ratio_5']

    return df


def add_cross_section_ranks(df: pd.DataFrame, rank_cols: list) -> pd.DataFrame:
    """
    添加全市场横截面Rank特征
    :param df: 全市场数据，包含 trade_date
    :param rank_cols: 需要计算Rank的列名列表
    :return: 包含横截面Rank特征的DataFrame
    """
    df = df.copy()
    for col in rank_cols:
        df[f'cs_rank_{col}'] = (
            df.groupby('trade_date')[col]
              .rank(pct=True)
        )
    return df


def add_label(df: pd.DataFrame, horizon=5) -> pd.DataFrame:
    """
    构建Label（5日调仓）
    :param df: 股票数据
    :param horizon: 预测周期
    :return: 包含Label的DataFrame
    """
    df = df.copy()
    df['label'] = np.log(df['P'].shift(-horizon) / df['P'].shift(-1))
    return df


def generate_feature_label(limit:int = 0):
    """
    生成特征和Label数据，按月处理并保存
    每处理100个文件就写入到文件，支持数据追加
    """
    # 数据目录
    input_dir = './stock_data/adj_daily'  # 使用复权后的数据
    output_dir = './stock_data/feature_label'
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有复权数据文件（使用前复权数据）
    input_files = glob.glob(os.path.join(input_dir, '*_qfq.csv'))
    
    # 测试代码只挑limit只股票
    if limit > 0:
        input_files = input_files[:limit]
        print(f"找到 {len(input_files)} 个股票数据文件，只处理前{limit}个用于测试")
    
    # 选择需要计算Rank的列
    rank_cols = [
        'mom_5', 'mom_10', 'mom_20', 'mom_20_5',
        'trend_5', 'trend_10', 'trend_20',
        'ma_ratio_5_20', 'ma_ratio_10_20',
        'range_5', 'range_20', 'range_ratio',
        'vol_ratio_5', 'vol_ratio_20', 'amount_ratio',
        'vol_price_corr_10', 'vol_price_corr_20',
        'vol_mom_5'
    ]
    
    processed_count = 0
    all_months = set()
    
    # 按批次处理，每批500个文件
    batch_size = 500
    total_batches = len(input_files) // batch_size + 1
    
    for batch_idx in range(total_batches):
        print(f"\n=== 处理批次 {batch_idx + 1}/{total_batches} ===")
        
        # 获取当前批次的文件
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(input_files))
        batch_files = input_files[start_idx:end_idx]
        
        if not batch_files:
            break
        
        # 批次内临时存储所有处理后的数据
        batch_processed_data = []
        
        # 处理当前批次的文件
        for file_path in batch_files:
            try:
                # 1. 读取数据
                df = pd.read_csv(file_path)
                
                # 2. 转换trade_date为日期类型
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
                df['year_month'] = df['trade_date'].dt.strftime('%Y%m')
                
                # 3. 计算单股票特征
                df = compute_features_single_stock(df)
                
                # 4. 先计算label（label不涉及截面特征，避免分月后回溯问题）
                df = add_label(df, horizon=5)
                
                # 5. 添加股票代码
                stock_code = os.path.basename(file_path).replace('stock_data_', '').replace('_qfq.csv', '')
                df['ts_code'] = stock_code
                
                # 6. 收集当前股票的所有月份
                all_months.update(df['year_month'].unique())
                
                # 7. 保存到批次数据中
                batch_processed_data.append(df)
                
                processed_count += 1
                
                if processed_count % 100 == 0:
                    print(f"已处理 {processed_count} 个股票")
                    
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {str(e)}")
                continue
        
        # 8. 合并批次内所有数据
        if batch_processed_data:
            batch_data = pd.concat(batch_processed_data, ignore_index=True)
            
            # 9. 确保月份有序
            all_months_sorted = sorted(all_months)
            
            # 10. 按月处理数据
            for month in all_months_sorted:
                # 11. 提取当月数据
                month_data = batch_data[batch_data['year_month'] == month].copy()
                if month_data.empty:
                    continue
                
                # 12. 计算当月的横截面Rank特征
                month_data = add_cross_section_ranks(month_data, rank_cols)
                
                # 13. 保存当月结果，支持追加
                output_file = os.path.join(output_dir, f'stock_feature_label_{month}.csv')
                
                # 14. 检查文件是否存在，存在则追加，不存在则创建
                if os.path.exists(output_file):
                    month_data.to_csv(output_file, mode='a', header=False, index=False)
                    print(f"{month}: 数据已追加到文件")
                else:
                    month_data.to_csv(output_file, index=False)
                    print(f"{month}: 数据已保存到新文件")
                
                # 15. 释放内存
                del month_data
            
            # 16. 释放批次数据内存
            del batch_data
            del batch_processed_data
    
    # 17. 总体统计信息
    print(f"\n所有文件处理完成")
    print(f"总处理股票数: {processed_count}")
    print(f"输出文件目录: {output_dir}")
    print(f"共生成 {len(all_months)} 个月份文件")
    
    # 18. 打印各月份文件大小信息
    all_months_sorted = sorted(all_months)
    print("\n各月份文件大小:")
    for month in all_months_sorted:
        output_file = os.path.join(output_dir, f'stock_feature_label_{month}.csv')
        if os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"{month}: {size_mb:.2f} MB")


if __name__ == "__main__":
    # generate_feature_label(limit=100)
    generate_feature_label(limit=0)
