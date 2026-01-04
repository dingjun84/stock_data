import backtrader as bt
import numpy as np

class PandasSignalData(bt.feeds.PandasData):
    """Backtrader数据feed，包含score"""
    lines = ('score',)
    params = (('score', -1),)


class XGBStrategy(bt.Strategy):
    """
    XGBoost策略，5日调仓，包含风险控制和止损机制
    """
    params = dict(
        rebalance_days=5,     # 调仓频率
        top_pct=0.05,         # 选股比例
        max_pct_per_stock=0.2, # 单只股票最大资金比例
        stop_loss_pct=0.1,   # 止损比例 (10%)
        score_threshold=0.0086   # 评分阈值，低于此值不买入
    )

    def __init__(self):
        """初始化策略"""
        self.day_count = 0
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        # 记录持仓成本，用于止损
        self.position_cost = {}

    def next(self):
        """策略主逻辑"""
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
    
    def notify_order(self, order):
        """订单状态通知"""
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

    def notify_trade(self, trade):
        """交易通知"""
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
            print(f"[{trade_date}]   统计: 胜率={win_rate:.2f}% (胜:{self.win_count}, 负:{self.loss_count})" )
            print("------------------------")
        elif trade.status == trade.Open:
            # 打印开仓信息
            print(f"[{trade_date}] 开仓: 股票={stock_code}, 价格={trade.price:.2f}, 数量={trade.size:.0f}")