import pandas as pd
import numpy as np
import os
import glob

class DataLoader:
    """
    数据加载和处理类
    """
    def __init__(self, data_dir):
        """
        初始化数据加载器
        :param data_dir: 数据目录
        """
        self.data_dir = data_dir
    
    def load_data(self, start_month=None, end_month=None):
        """
        从多个月份文件加载数据
        :param start_month: 开始月份 (格式: YYYYMM)
        :param end_month: 结束月份 (格式: YYYYMM)
        :return: 合并后的数据
        """
        # 获取所有月份文件
        file_pattern = os.path.join(self.data_dir, 'stock_feature_label_*.csv')
        files = glob.glob(file_pattern)
        
        # 筛选指定月份范围的文件
        if start_month or end_month:
            filtered_files = []
            for file in files:
                # 提取文件名中的月份
                filename = os.path.basename(file)
                month = filename.replace('stock_feature_label_', '').replace('.csv', '')
                
                # 检查是否在指定范围内
                if (not start_month or month >= start_month) and (not end_month or month <= end_month):
                    filtered_files.append(file)
            files = filtered_files
        
        print(f"找到 {len(files)} 个数据文件")
        
        # 合并所有文件
        dfs = []
        for file in files:
            print(f"加载文件: {file}")
            df = pd.read_csv(file)
            dfs.append(df)
        
        if not dfs:
            return pd.DataFrame()  # 返回空的 DataFrame，避免后续 concat 报错
        
        # 合并数据
        df = pd.concat(dfs, ignore_index=True)
        print(f"数据合并完成，总样本数: {len(df)}")
        
        return df
    
    def build_train_set(self, df, feature_cols, stock_list=None):
        """
        构建训练集
        :param df: 特征和标签数据
        :param feature_cols: 特征列名列表
        :param stock_list: 可选，股票代码列表，用于过滤数据
        :return: X (特征), y (标签)
        """
        # 复制数据，避免修改原始数据
        df = df.copy()
        
        # 根据股票列表过滤数据
        if stock_list:
            df = df[df['ts_code'].isin(stock_list)]
            print(f"根据股票列表过滤后，剩余样本数: {len(df)}")
        
        # 检查数据质量
        print(f"训练数据中NaN值情况:")
        print(df.isnull().sum())
        
        # 处理inf值，替换为NaN
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # 删除包含NaN值的行
        df = df.dropna(subset=feature_cols + ['label'])
        
        X = df[feature_cols]
        y = df['label']
        # 打印记录条数
        print(f"训练集样本数: {len(X)}")
        return X, y
    
    def prepare_backtest_data(self, df, stock_list=None, select_percent=None):
        """
        准备回测数据
        :param df: 包含score的完整数据
        :param stock_list: 可选，股票代码列表，用于过滤数据
        :param select_percent: 可选，选择股票的比例（0-1），用于只选择部分股票
        :return: 按股票代码分组的回测数据
        """
        # 保留需要的列
        backtest_cols = ['trade_date', 'ts_code', 'open', 'high', 'low', 'close', 'vol', 'score']
        df_backtest = df[backtest_cols].copy()
        
        # 根据股票列表过滤数据
        if stock_list:
            df_backtest = df_backtest[df_backtest['ts_code'].isin(stock_list)]
            print(f"根据股票列表过滤后，剩余样本数: {len(df_backtest)}")
            print(f"剩余股票数: {df_backtest['ts_code'].nunique()}")
        
        # 数据格式检查
        print(f"原始数据样本数: {len(df_backtest)}")
        print(f"原始trade_date格式: {df_backtest['trade_date'].dtype}")
        print(f"示例trade_date值: {df_backtest['trade_date'].iloc[0]}")
        
        # 确保trade_date格式正确 - 自动推断格式
        df_backtest['trade_date'] = pd.to_datetime(df_backtest['trade_date'])
        print(f"转换后trade_date格式: {df_backtest['trade_date'].dtype}")
        print(f"日期范围: {df_backtest['trade_date'].min()} 到 {df_backtest['trade_date'].max()}")
        
        # 检查数据质量
        print(f"数据中NaN值情况:")
        print(df_backtest.isnull().sum())
        
        # 如果需要只选择部分股票
        selected_stocks = None
        if select_percent and 0 < select_percent <= 1:
            # 获取所有股票代码
            all_stocks = df_backtest['ts_code'].unique()
            # 计算需要选择的股票数量
            select_count = max(1, int(len(all_stocks) * select_percent))
            # 随机选择股票（这里简单起见，直接取前N个，实际可以根据需要调整选择逻辑）
            selected_stocks = all_stocks[:select_count]
            # 过滤数据
            df_backtest = df_backtest[df_backtest['ts_code'].isin(selected_stocks)]
            print(f"按比例 {select_percent*100}% 选择股票，选择数量: {select_count}")
        
        # 按股票代码分组
        stock_data_dict = {}
        for ts_code, group in df_backtest.groupby('ts_code'):
            # 按日期排序（升序）
            group = group.sort_values('trade_date', ascending=True)
            
            # 直接设置trade_date为索引
            group = group.set_index('trade_date', drop=True)
            
            # 检查分组后的数据
            if len(group) > 0:
                stock_data_dict[ts_code] = group
        
        print(f"共处理 {len(stock_data_dict)} 只股票")
        
        return stock_data_dict