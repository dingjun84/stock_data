import sys
import os
from datetime import datetime
from data_processing.data_loader import DataLoader
from model_training.xgb_model import XGBModel
from backtest.backtest_runner import BacktestRunner
from util.util import HS1000, HS300

# 定义常量
DATA_DIR = '../stock_data/feature_label'  # 特征标签数据目录
MODEL_DIR = './models'  # 模型保存目录
RESULT_DIR = './results'  # 结果保存目录
FEATURE_COLS = [
    'mom_5','mom_10','mom_20','mom_20_5',
    'trend_5','trend_10','trend_20',
    'ma_ratio_5_20','ma_ratio_10_20',
    'range_5','range_20','range_ratio',
    'body','upper_shadow','lower_shadow','shadow_ratio',
    'vol_ratio_5','vol_ratio_20',
    'amount_ratio',
    'vol_price_corr_10','vol_price_corr_20',
    'vol_mom_5',
    'cs_rank_mom_20_5',
    'cs_rank_trend_20',
    'cs_rank_range_20',
    'cs_rank_vol_ratio_20',
    'cs_rank_amount_ratio',
]

def getStartAndEnd(preEndYear:int,preEndMonth:int,incremental_months=3):
    startYear = preEndYear
    startMonth = preEndMonth+1
    if startMonth > 12:
            startMonth -= 12
            startYear += 1

    endYear = startYear
    endMonth = startMonth + incremental_months -1
    if endMonth > 12:
            endMonth -= 12
            endYear += 1
    return (startYear,startMonth,endYear,endMonth)

def full_strategy(start_year=2020,start_month=1, train_months=36, test_months=3, incremental_months=3):
    """
    完整策略实现
    :param start_year: 开始年份
    :param train_years: 初始训练年数
    :param test_months: 测试月数
    :param incremental_months: 增量训练月数
    """
    # 初始化组件
    data_loader = DataLoader(DATA_DIR)
    model = XGBModel(os.path.join(MODEL_DIR, 'xgb_model.pkl'))
    backtest_runner = BacktestRunner()
    
    incre_years = train_months // 12
    incre_months = train_months % 12

    end_year = start_year + incre_years
    end_month = start_month+incre_months
    if end_month > 12:
        end_month -= 12
        end_year += 1


    # 初始训练阶段：训练3年数据
    initial_train_start = f"{start_year}{start_month:02d}"
    initial_train_end = f"{end_year}{end_month:02d}"
    print(f"\n=== 初始训练阶段: {initial_train_start} 到 {initial_train_end} ===")
    
    # 加载初始训练数据
    df_train = data_loader.load_data(initial_train_start, initial_train_end)
    if df_train.empty:
        print(f"\n=== 初始回测 {initial_train_start} 到 {initial_train_end} 数据为空===")
        return
    # 构建训练集 - 只使用HS1000股票
    X, y = data_loader.build_train_set(df_train, FEATURE_COLS, HS1000)
    print(f"训练集构建完成，特征数: {X.shape[1]}, 样本数: {X.shape[0]}")
    
    # 训练模型
    model.train(X, y)
    
    # 初始回测阶段：测试接下来3个月
    start_year,start_month,end_year,end_month = getStartAndEnd(end_year,end_month)
    initial_test_start = f"{start_year}{start_month:02d}"
    initial_test_end = f"{end_year}{end_month:02d}"
    print(f"\n=== 初始回测阶段: {initial_test_start} 到 {initial_test_end} ===")
    
    # 加载初始回测数据
    df_test = data_loader.load_data(initial_test_start, initial_test_end)
    if df_test.empty:
        print(f"\n=== 初始回测 {initial_test_start} 到 {initial_test_end} 数据为空===")
        return
    
    # 生成预测score
    df_with_score = model.predict(df_test, FEATURE_COLS)
    print(f"预测完成，有效score数: {df_with_score['score'].notna().sum()}")
    
    # 准备回测数据 - 只使用HS300股票并选择5%的股票
    stock_data_dict = data_loader.prepare_backtest_data(df_with_score, stock_list=HS300)
    
    # 运行回测
    backtest_result = backtest_runner.run_backtest(stock_data_dict, save_results=True, output_dir=RESULT_DIR)
    
    
    
    while True:  # 假设数据到2025年为止
        # 计算增量训练和回测的月份范围
        # 增量训练和回测阶段
        start_year,start_month,end_year,end_month = getStartAndEnd(end_year,end_month)
        train_start = f"{start_year}{start_month:02d}"
        
        # 计算训练结束月份
        train_end = f"{end_year}{end_month:02d}"
        
        test_start_year,test_start_month,test_end_year,test_end_month = getStartAndEnd(end_year,end_month)
        test_start = f"{test_start_year}{test_start_month:02d}"
        
        test_end = f"{test_end_year}{test_end_month:02d}"
        
        
        # 增量训练阶段
        print(f"\n=== 增量训练阶段: {train_start} 到 {train_end} ===")
        
        # 加载增量训练数据
        df_train = data_loader.load_data(train_start, train_end)
        if df_train.empty:
            print(f"\n=== 增量训练 {train_start} 到 {train_end} 数据为空===")
            return
        
        # 重新构建训练集 - 只使用HS1000股票
        X, y = data_loader.build_train_set(df_train, FEATURE_COLS, HS1000)
        print(f"增量训练集构建完成，特征数: {X.shape[1]}, 样本数: {X.shape[0]}")
        
        # 增量训练模型
        model.train(X, y, incremental=True, num_boost_round=50)
        
        # 增量回测阶段
        print(f"\n=== 增量回测阶段: {test_start} 到 {test_end} ===")
        
        # 加载回测数据
        df_test = data_loader.load_data(test_start, test_end)
        if df_test.empty:
            print(f"\n=== 测试 {test_start} 到 {test_end} 数据为空===")
            return

        # 生成预测score
        df_with_score = model.predict(df_test, FEATURE_COLS)
        print(f"预测完成，有效score数: {df_with_score['score'].notna().sum()}")
        
        # 准备回测数据 - 只使用HS300股票并选择5%的股票
        stock_data_dict = data_loader.prepare_backtest_data(df_with_score, stock_list=HS300)
        
        # 运行回测
        backtest_result = backtest_runner.run_backtest(stock_data_dict, save_results=True, output_dir=RESULT_DIR)
        
    
    # 保存最终结果
    backtest_runner.save_results(RESULT_DIR)
    
    print(f"\n=== 完整策略执行完成 ===")
    print(f"回测结果已保存到: {os.path.join(RESULT_DIR, 'backtest_results.csv')}")



if __name__ == "__main__":
    #每次训练开启一个新的目录，路径为时间戳
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    MODEL_DIR = os.path.join(MODEL_DIR, timestamp)
    RESULT_DIR = os.path.join(RESULT_DIR, timestamp)
    # 确保目录存在
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(RESULT_DIR, exist_ok=True)
    
    # 处理命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "full":
        # 运行完整策略
        full_strategy()
    else:
        # 运行测试策略 - 只训练一个月回测一个月
        # 示例：训练202411，回测202412
        full_strategy(start_year=2024,start_month=1, train_months=3, test_months=3, incremental_months=3)