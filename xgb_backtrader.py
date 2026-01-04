import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
import backtrader as bt
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# 定义常量
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

# 数据和模型路径
DATA_DIR = './stock_data/feature_label'  # 特征标签数据目录
MODEL_PATH = './xgboost/xgb_model.pkl'



def build_train_set(df):
    """
    构建训练集
    :param df: 特征和标签数据
    :return: X (特征), y (标签)
    """
    # 复制数据，避免修改原始数据
    df = df.copy()
    
    # 处理inf值，替换为NaN
    df = df.replace([np.inf, -np.inf], np.nan)
    
    # 删除包含NaN值的行
    df = df.dropna(subset=FEATURE_COLS + ['label'])
    
    X = df[FEATURE_COLS]
    y = df['label']
    
    return X, y


def train_xgb(X, y, model_path):
    """
    训练XGBoost模型并保存
    :param X: 特征数据
    :param y: 标签数据
    :param model_path: 模型保存路径
    :return: 训练好的模型
    """
    print("开始训练XGBoost模型...")
    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        max_depth=5,
        n_estimators=300,
        learning_rate=0.05,
        subsample=0.7,
        colsample_bytree=0.7,
        random_state=42
    )
    model.fit(X, y)
    
    # 创建模型保存目录
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    # 保存模型
    joblib.dump(model, model_path)
    print(f"模型已保存到: {model_path}")
    
    # 打印特征重要性
    print("\n特征重要性:")
    for i, col in enumerate(FEATURE_COLS):
        print(f"{col}: {model.feature_importances_[i]:.4f}")
    
    return model


def load_xgb_model(model_path):
    """
    加载XGBoost模型
    :param model_path: 模型保存路径
    :return: 加载的模型
    """
    print(f"从{model_path}加载XGBoost模型...")
    model = joblib.load(model_path)
    print(f"模型加载完成")
    return model


def predict_score(df, model):
    """
    使用模型预测并生成score
    :param df: 特征数据
    :param model: 训练好的模型
    :return: 包含score的DataFrame
    """
    df = df.copy()
    # 只对有完整特征的数据进行预测
    valid_mask = df[FEATURE_COLS].notna().all(axis=1)
    df.loc[valid_mask, 'score'] = model.predict(df[valid_mask][FEATURE_COLS])
    df.loc[~valid_mask, 'score'] = np.nan
    return df


def calc_rank_ic(df, feature, label='label'):
    """
    计算Rank IC
    :param df: 数据
    :param feature: 特征名
    :param label: 标签名
    :return: 每日Rank IC
    """
    return (
        df.groupby('trade_date')
          .apply(lambda x: x[feature].corr(x[label], method='spearman'))
    )


def feature_ic_report(df, features):
    """
    生成特征IC报告
    :param df: 数据
    :param features: 特征列表
    :return: IC报告DataFrame
    """
    report = {}
    for f in features:
        ic = calc_rank_ic(df, f)
        report[f] = {
            'mean_ic': ic.mean(),
            'std_ic': ic.std(),
            'ir': ic.mean() / ic.std() if ic.std() > 0 else 0,
            'positive_ratio': (ic > 0).mean()
        }
    return pd.DataFrame(report).T


def temporal_ic_compare(df, feature, split_date):
    """
    时间切分的IC比较
    :param df: 数据
    :param feature: 特征名
    :param split_date: 切分日期
    :return: 训练集和测试集的IC比较
    """
    ic = calc_rank_ic(df, feature)
    # 确保索引和split_date类型一致
    ic_index_str = ic.index.astype(str)
    split_date_str = str(split_date)
    train_ic = ic[ic_index_str <= split_date_str]
    test_ic = ic[ic_index_str > split_date_str]
    return {
        'train_mean': train_ic.mean(),
        'test_mean': test_ic.mean(),
        'decay_ratio': test_ic.mean() / train_ic.mean() if train_ic.mean() != 0 else 0
    }


# Backtrader相关代码
class PandasSignalData(bt.feeds.PandasData):
    """Backtrader数据feed，包含score"""
    lines = ('score',)
    params = (('score', -1),)


class XGBStrategy(bt.Strategy):
    """XGBoost策略，5日调仓"""
    params = dict(
        rebalance_days=5,     # 调仓频率
        top_pct=0.1,         # 选股比例
        max_pct_per_stock=0.2, # 单只股票最大资金比例
        stop_loss_pct=0.05,   # 止损比例 (5%)
        score_threshold=0.0   # 评分阈值，低于此值不买入
    )

    def __init__(self):
        self.day_count = 0
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        # 记录持仓成本，用于止损
        self.position_cost = {}

    def next(self):
        self.day_count += 1
        
        # 调试信息：打印当前日期和score情况
        if self.day_count % 10 == 0:
            scores = [d.score[0] for d in self.datas if not np.isnan(d.score[0])]
            print(f"日期: {self.datas[0].datetime.date(0)}, score可用股票数: {len(scores)}")
            if scores:
                print(f"score范围: {min(scores):.4f} - {max(scores):.4f}")
        
        # 止损逻辑
        self.apply_stop_loss()
        
        # 每5天调仓一次
        if self.day_count % self.p.rebalance_days != 0:
            return

        # 获取所有数据的score
        scores = [(d, d.score[0]) for d in self.datas if not np.isnan(d.score[0])]
        print(f"调仓日({self.day_count}): 可用股票数={len(scores)}")
        if not scores:
            print("没有可用score数据，跳过调仓")
            return

        # 按score降序排序，选择top N%
        scores.sort(key=lambda x: x[1], reverse=True)
        top_n = max(1, int(len(scores) * self.p.top_pct))  # 至少选择1只股票
        print(f"选择前{top_n}只股票")
        
        # 只选择评分高于阈值的股票
        selected = []
        for d, score in scores[:top_n]:
            if score >= self.p.score_threshold:
                selected.append((d, score))
        
        if not selected:
            print("没有评分符合阈值的股票，跳过调仓")
            return
        
        selected_datas = {d for d, _ in selected}
        
        # 计算每只股票的目标仓位
        # 等权重分配，但不超过单只股票最大比例
        base_pct = 1.0 / len(selected)
        target_pct = min(base_pct, self.p.max_pct_per_stock)
        
        print(f"每只股票目标仓位: {target_pct:.2%}")

        # 调仓：卖出未选中的股票，买入选中的股票
        # 1. 先卖出未选中的股票
        for d, score in scores:
            pos = self.getposition(d).size
            if d not in selected_datas and pos != 0:
                # 卖出未选中的股票
                self.order_target_percent(d, 0)
                print(f"卖出 {d._name}, 评分={score:.4f}")
                self.trade_count += 1
                if d in self.position_cost:
                    del self.position_cost[d]
        
        # 2. 再买入选中的股票
        for d, score in selected:
            pos = self.getposition(d).size
            if pos == 0:
                # 买入选中的股票，控制单只股票最大仓位
                self.order_target_percent(d, target_pct)
                print(f"买入 {d._name}, 评分={score:.4f}")
                self.trade_count += 1
        
        print(f"本次调仓完成，累计交易次数: {self.trade_count}")
        
    def apply_stop_loss(self):
        """应用止损逻辑"""
        for d in self.datas:
            pos = self.getposition(d).size
            if pos != 0:
                current_price = d.close[0]
                cost_price = self.getposition(d).price
                
                # 计算跌幅
                drop_pct = (cost_price - current_price) / cost_price
                
                # 如果跌幅超过止损比例，执行止损
                if drop_pct >= self.p.stop_loss_pct:
                    print(f"[{self.datas[0].datetime.date(0)}] 止损: 股票={d._name}, 成本价={cost_price:.2f}, 当前价={current_price:.2f}, 跌幅={drop_pct:.2%}")
                    self.order_target_percent(d, 0)
                    self.trade_count += 1
                    if d in self.position_cost:
                        del self.position_cost[d]
    
    # 订单状态通知方法，当订单状态发生变化时被调用
    def notify_order(self, order):
        # 定义订单状态名称映射
        status_names = {
            order.Submitted: '已提交',
            order.Accepted: '已接受',
            order.Completed: '已完成',
            order.Canceled: '已取消',
            order.Rejected: '已拒绝',
            order.Margin: '保证金不足',
            order.Partial: '部分成交'
        }
        
        # 获取订单相关信息
        stock_code = order.data._name
        order_date = order.data.datetime.date(0)
        order_type = '买入' if order.isbuy() else '卖出'
        status_name = status_names.get(order.status, '未知')
        
        # 打印所有订单状态变化
        print(f"[{order_date}] 订单状态: 股票={stock_code}, 类型={order_type}, 状态={status_name}")

        # 如果订单已完成
        if order.status == order.Completed:
            if order.isbuy():
                # 打印买入执行信息
                print(f"[{order_date}] ****买入成交: 股票={stock_code}, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 佣金: {order.executed.comm:.2f}")
            elif order.issell():
                # 打印卖出执行信息
                print(f"[{order_date}] ====卖出成交: 股票={stock_code}, 价格: {order.executed.price:.2f}, 金额: {order.executed.value:.2f}, 佣金: {order.executed.comm:.2f}")

    # 交易通知方法，当交易状态变化时被调用
    def notify_trade(self, trade):
        # 获取交易相关信息
        stock_code = trade.data._name
        trade_date = trade.data.datetime.date(0)
        trade_status = '已平仓' if trade.status == trade.Closed else '开仓中'
        
        # 打印交易状态变化
        print(f"[{trade_date}] 交易状态: 股票={stock_code}, 状态={trade_status}")
        
        if trade.status == trade.Closed:
            # 更新交易统计
            if trade.pnlcomm > 0:
                self.win_count += 1
            else:
                self.loss_count += 1
            
            # 获取账户信息
            cash = self.broker.get_cash()
            value = self.broker.get_value()
            
            # 计算胜率
            total_trades = self.win_count + self.loss_count
            win_rate = self.win_count / total_trades * 100 if total_trades > 0 else 0
            
            # 打印详细交易信息
            print(f"[{trade_date}] 交易完成: 股票={stock_code}")
            print(f"[{trade_date}]   盈亏: 总盈亏={trade.pnl:.2f}, 扣除佣金={trade.pnlcomm:.2f}")
            print(f"[{trade_date}]   账户: 现金={cash:.2f}, 总价值={value:.2f}")
            print(f"[{trade_date}]   统计: 胜率={win_rate:.2f}% (胜:{self.win_count}, 负:{self.loss_count})")
            print("------------------------")
        elif trade.status == trade.Open:
            # 打印开仓信息
            print(f"[{trade_date}] 开仓: 股票={stock_code}, 价格={trade.price:.2f}, 数量={trade.size:.0f}")


def prepare_backtest_data(df):
    """
    准备回测数据
    :param df: 包含score的完整数据
    :return: 按股票代码分组的回测数据
    """
    # 保留需要的列
    backtest_cols = ['trade_date', 'ts_code', 'open', 'high', 'low', 'close', 'vol', 'score']
    df_backtest = df[backtest_cols].copy()
    
    # 数据格式检查
    print(f"原始数据样本数: {len(df_backtest)}")
    print(f"原始trade_date格式: {df_backtest['trade_date'].dtype}")
    print(f"示例trade_date值: {df_backtest['trade_date'].iloc[0]}")
    
    # 确保trade_date格式正确 - 自动推断格式，因为数据中的日期已经是YYYY-MM-DD格式
    df_backtest['trade_date'] = pd.to_datetime(df_backtest['trade_date'])  # 移除format参数，让pandas自动推断
    print(f"转换后trade_date格式: {df_backtest['trade_date'].dtype}")
    print(f"日期范围: {df_backtest['trade_date'].min()} 到 {df_backtest['trade_date'].max()}")
    
    # 检查数据质量
    print(f"数据中NaN值情况:")
    print(df_backtest.isnull().sum())
    
    # 按股票代码分组
    stock_data_dict = {}
    for ts_code, group in df_backtest.groupby('ts_code'):
        # 按日期排序（升序）
        group = group.sort_values('trade_date', ascending=True)
        
        # 直接设置trade_date为索引，不重置索引
        group = group.set_index('trade_date', drop=True)
        
        # 检查分组后的数据
        if len(group) > 0:
            stock_data_dict[ts_code] = group
    
    print(f"共处理 {len(stock_data_dict)} 只股票")
    # 打印第一只股票的数据信息
    if stock_data_dict:
        first_stock = next(iter(stock_data_dict.keys()))
        first_df = stock_data_dict[first_stock]
        print(f"\n第一只股票 {first_stock} 的数据信息:")
        print(f"样本数: {len(first_df)}")
        print(f"索引类型: {first_df.index.dtype}")
        print(f"索引范围: {first_df.index.min()} 到 {first_df.index.max()}")
        print(f"列名: {list(first_df.columns)}")
        print(f"前3行数据:")
        print(first_df.head(3))
    
    return stock_data_dict


def run_backtest(stock_data_dict):
    """
    运行Backtrader回测
    :param stock_data_dict: 按股票代码分组的回测数据
    """
    print(f"开始回测，共 {len(stock_data_dict)} 只股票")
    
    # 创建Cerebro实例
    cerebro = bt.Cerebro()
    
    # 添加数据
    for ts_code, df in stock_data_dict.items():
        # 只添加有score数据的股票
        if df['score'].notna().any():
            data = PandasSignalData(
                dataname=df,
                openinterest=-1,  # 不使用openinterest
                open='open',
                high='high',
                low='low',
                close='close',
                volume='vol',
                score='score'
            )
            cerebro.adddata(data, name=ts_code)
    
    # 添加策略
    cerebro.addstrategy(XGBStrategy)
    
    # 设置初始资金
    cerebro.broker.setcash(1000000.0)
    
    # 设置佣金（万分之3）
    cerebro.broker.setcommission(commission=0.0003)
    
    # 设置每次交易的滑点（千分之1）
    cerebro.broker.set_slippage_perc(perc=0.001)
    
    # 添加分析器 - 只使用核心分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    
    # 运行回测
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    
    # 打印回测结果
    strat = results[0]
    final_value = cerebro.broker.getvalue()
    print(f"最终资金: {final_value:.2f}")
    
    # 处理夏普比率为None的情况
    sharpe_result = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe_result.get('sharperatio', None)
    if sharpe_ratio is not None:
        print(f"夏普比率: {sharpe_ratio:.4f}")
    else:
        print("夏普比率: None (无交易发生或数据不足)")
    
    # 打印最大回撤和总收益率
    drawdown_result = strat.analyzers.drawdown.get_analysis()
    print(f"最大回撤: {drawdown_result['max']['drawdown']:.4f}%")
    
    returns_result = strat.analyzers.returns.get_analysis()
    print(f"总收益率: {returns_result['rtot']:.4f}")
    
    # 打印交易分析结果
    trade_analyzer = strat.analyzers.trade_analyzer.get_analysis()
    if 'total' in trade_analyzer and 'total' in trade_analyzer['total']:
        total_trades = trade_analyzer['total']['total']
        print(f"总交易次数: {total_trades}")
        
        if total_trades > 0:
            if 'won' in trade_analyzer and 'total' in trade_analyzer['won']:
                won_trades = trade_analyzer['won']['total']
                win_rate = won_trades / total_trades * 100
                print(f"胜率: {win_rate:.2f}%")
            
            if 'pnl' in trade_analyzer and 'net' in trade_analyzer['pnl']:
                total_pnl = trade_analyzer['pnl']['net']['total']
                avg_pnl = trade_analyzer['pnl']['net']['average']
                print(f"总盈亏: {total_pnl:.2f}")
                print(f"平均每笔盈亏: {avg_pnl:.2f}")
    
    # 打印策略自定义统计
    total_trades = strat.win_count + strat.loss_count
    if total_trades > 0:
        win_rate = round(strat.win_count * 100.0 / total_trades, 2)
        print(f"策略自定义胜负率：{win_rate}% 胜利次数: {strat.win_count}，失败次数: {strat.loss_count}，总交易次数: {total_trades}")
    else:
        print(f"策略自定义胜负率：0.00% 胜利次数: {strat.win_count}，失败次数: {strat.loss_count}，总交易次数: {total_trades} (无已结束交易)")

    # 暂时禁用图表绘制，避免内存错误
    # cerebro.plot(style='candle')


def load_data_from_multiple_files(data_dir, start_month=None, end_month=None):
    """
    从多个月份文件加载数据
    :param data_dir: 数据目录
    :param start_month: 开始月份 (格式: YYYYMM)
    :param end_month: 结束月份 (格式: YYYYMM)
    :return: 合并后的数据
    """
    import glob
    
    # 获取所有月份文件
    file_pattern = os.path.join(data_dir, 'stock_feature_label_*.csv')
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
        raise ValueError("未找到符合条件的数据文件")
    
    # 合并数据
    df = pd.concat(dfs, ignore_index=True)
    print(f"数据合并完成，总样本数: {len(df)}")
    
    return df


def main():
    """
    主函数
    """
    # 1. 加载数据 - 支持从多个月份文件加载
    print("加载特征和标签数据...")
    # 示例：加载2024年12月的数据
    df = load_data_from_multiple_files(DATA_DIR, start_month='202412', end_month='202412')
    print(f"数据加载完成，总样本数: {len(df)}")
    
    # 2. 构建训练集
    X, y = build_train_set(df)
    print(f"训练集构建完成，特征数: {X.shape[1]}, 样本数: {X.shape[0]}")
    
    # 3. 训练模型
    # model = train_xgb(X, y, MODEL_PATH)
    # 从模型路径加载模型
    model = load_xgb_model(MODEL_PATH)
    
    # 4. 生成预测score
    df_with_score = predict_score(df, model)
    print(f"预测完成，有效score数: {df_with_score['score'].notna().sum()}")
    
    # # 5. 特征IC分析
    # print("\n特征IC报告:")
    # ic_report = feature_ic_report(df, FEATURE_COLS)
    # print(ic_report.sort_values('ir', ascending=False).head(10))
    # 
    # # 6. 时间稳定性分析（示例：使用2024年作为测试集）
    # print("\n特征时间稳定性分析:")
    # split_date = '20240101'
    # for feature in FEATURE_COLS[:5]:  # 只显示前5个特征
    #     result = temporal_ic_compare(df, feature, split_date)
    #     print(f"{feature}: 训练IC={result['train_mean']:.4f}, 测试IC={result['test_mean']:.4f}, 衰减比={result['decay_ratio']:.4f}")
    
    # 7. 准备回测数据
    print("\n准备回测数据...")
    stock_data_dict = prepare_backtest_data(df_with_score)
    print(f"回测数据准备完成，共 {len(stock_data_dict)} 只股票")
    
    # 8. 运行回测
    # 注意：完整回测需要大量计算资源，这里只使用前10只股票进行示例
    sample_stock_data = dict(list(stock_data_dict.items())[:100])
    run_backtest(sample_stock_data)


if __name__ == "__main__":
    main()
