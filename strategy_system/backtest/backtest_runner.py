import backtrader as bt
import pandas as pd
import os
from strategy.xgb_strategy import XGBStrategy, PandasSignalData

class BacktestRunner:
    """
    回测运行器，负责运行回测并保存结果
    """
    def __init__(self, initial_cash=1000000.0, commission=0.0003, slippage=0.001):
        """
        初始化回测运行器
        :param initial_cash: 初始资金
        :param commission: 佣金比例
        :param slippage: 滑点比例
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.results = []
    
    def run_backtest(self, stock_data_dict, strategy_params=None, save_results=False, output_dir=None):
        """
        运行Backtrader回测
        :param stock_data_dict: 按股票代码分组的回测数据
        :param strategy_params: 策略参数
        :param save_results: 是否保存结果
        :param output_dir: 结果保存目录
        :return: 回测结果
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
        if strategy_params:
            cerebro.addstrategy(XGBStrategy, **strategy_params)
        else:
            cerebro.addstrategy(XGBStrategy)
        
        # 设置初始资金
        cerebro.broker.setcash(self.initial_cash)
        
        # 设置佣金（万分之3）
        cerebro.broker.setcommission(commission=self.commission)
        
        # 设置每次交易的滑点（千分之1）
        cerebro.broker.set_slippage_perc(perc=self.slippage)
        
        # 添加分析器
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
        
        # 处理夏普比率
        sharpe_result = strat.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe_result.get('sharperatio', None)
        if sharpe_ratio is not None:
            print(f"夏普比率: {sharpe_ratio:.4f}")
        else:
            print("夏普比率: None (无交易发生或数据不足)")
        
        # 打印最大回撤和总收益率
        drawdown_result = strat.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown_result['max']['drawdown']
        print(f"最大回撤: {max_drawdown:.4f}%")
        
        returns_result = strat.analyzers.returns.get_analysis()
        total_return = returns_result['rtot']
        print(f"总收益率: {total_return:.4f}")
        
        # 打印交易分析结果
        trade_analyzer = strat.analyzers.trade_analyzer.get_analysis()
        total_trades = 0
        win_rate = 0
        total_pnl = 0
        avg_pnl = 0
        
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
        strategy_total_trades = strat.win_count + strat.loss_count
        strategy_win_rate = 0
        if strategy_total_trades > 0:
            strategy_win_rate = round(strat.win_count * 100.0 / strategy_total_trades, 2)
            print(f"策略自定义胜负率：{strategy_win_rate}% 胜利次数: {strat.win_count}，失败次数: {strat.loss_count}，总交易次数: {strategy_total_trades}")
        else:
            print(f"策略自定义胜负率：0.00% 胜利次数: {strat.win_count}，失败次数: {strat.loss_count}，总交易次数: {strategy_total_trades} (无已结束交易)")
        
        # 构造回测结果字典
        backtest_result = {
            'initial_value': self.initial_cash,
            'final_value': final_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'strategy_total_trades': strategy_total_trades,
            'strategy_win_rate': strategy_win_rate
        }
        
        # 保存结果到列表
        self.results.append(backtest_result)
        
        # 保存结果到CSV
        if save_results:
            self.save_results(output_dir)
        
        return backtest_result
    
    def save_results(self, output_dir=None):
        """
        保存回测结果到CSV
        :param output_dir: 结果保存目录
        """
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'backtest_results.csv')
        else:
            output_file = 'backtest_results.csv'
        
        df = pd.DataFrame(self.results)
        df.to_csv(output_file, index=False)
        print(f"回测结果已保存到: {output_file}")
    
    def get_results(self):
        """
        获取回测结果
        :return: 回测结果列表
        """
        return self.results