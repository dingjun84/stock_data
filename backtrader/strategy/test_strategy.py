import backtrader as bt

# TestStrategy是一个简单的backtrader测试策略类
# 基于收盘价与开盘价的比较来决定买入或卖出操作
class TestStrategy(bt.Strategy):
    # 初始化方法，设置策略的初始状态
    def __init__(self):
        # 用于跟踪当前未完成的订单
        # 初始值为None，表示当前没有待处理的订单
        self.order = None

    # 核心交易逻辑方法，在每个K线周期执行一次
    def next(self):
        # 检查是否有未完成的订单，如果有则不提交新订单
        if self.order:
            print(f"Order {self.order.ref} is pending")
            return

        # 交易逻辑：如果当天收盘价高于开盘价，则考虑买入
        if self.datas[0].close > self.datas[0].open:
            # 如果已经持有多头头寸，则不重复买入
            if self.position.size > 0:
                return
            
            # 提交买入订单
            order = self.buy()
            # 打印买入订单信息，包括日期、订单大小和当前持仓信息
            print(f"****submit buy order,  date: {self.datas[0].datetime.date(0)},size:{order.size},position:{self.position.size}*{self.position.price}={self.position.size*self.position.price}")
        # 否则（收盘价低于或等于开盘价），考虑卖出
        else:
            # 如果没有持仓或持有空头头寸，则不卖出
            if self.position.size <= 0:
                return
            # 提交卖出订单
            order = self.sell()
            # 打印卖出订单信息，包括日期、订单大小和当前持仓信息
            print(f"====submit sell order, date: {self.datas[0].datetime.date(0)},size:{order.size},position:{self.position.size}*{self.position.price}={self.position.size*self.position.price}")

    # 订单状态通知方法，当订单状态发生变化时被调用
    def notify_order(self, order):
        # 打印订单各状态的注释代码（已注释）
        # print(f"submit:{order.Submitted}, Accepted:{order.Accepted}, Completed:{order.Completed}, Canceled:{order.Canceled}, Rejected:{order.Rejected},Margin:{order.Margin},Partial:{order.Partial}")
        
        # 如果订单处于提交或已接受状态，则不做处理
        if order.status in [order.Submitted, order.Accepted]:
            return

        # 如果订单已完成
        if order.status == order.Completed:
            # 判断是买入订单
            if order.isbuy():
                # 打印买入执行信息，包括日期、执行价格、成本、佣金和持仓信息
                print(f"****date: {self.datas[0].datetime.date(0)},Buy executed, price: {order.executed.price}, cost: {order.executed.value}, commission: {order.executed.comm},status:{order.status},size:{order.size},position:{self.position.size}*{self.position.price}={self.position.size*self.position.price}")
            # 判断是卖出订单
            elif order.issell():
                # 打印卖出执行信息，包括日期、执行价格、成本、佣金和持仓信息
                print(f"====date: {self.datas[0].datetime.date(0)},Sell executed, price: {order.executed.price}, cost: {order.executed.value}, commission: {order.executed.comm},status:{order.status},size:{order.size},position:{self.position.size}*{self.position.price}={self.position.size*self.position.price}")
        
            # 订单完成后，清空order变量，允许提交新订单
            self.order = None

    # 交易通知方法，当交易完成（平仓）时被调用
    def notify_trade(self, trade):
        # 打印交易的净利润和毛利
        # trade.pnlcomm: 考虑佣金后的净利润
        # trade.pnl: 不考虑佣金的毛利
        print(f"Trade closed, profit: {trade.pnlcomm}, {trade.pnl}")
        # 打印当前持仓状态
        print(self.position)