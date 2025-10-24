import backtrader as bt

class TestStrategy(bt.Strategy):
    def __init__(self):
        self.order = None

    def next(self):
        if self.order:
            print(f"Order {self.order.ref} is pending")
            return

        if self.datas[0].close > self.datas[0].open:
            order = self.buy()
            print(f"****submit buy order,  date: {self.datas[0].datetime.date(0)},size:{order.size},position:{self.position.size}*{self.position.price}={self.position.size*self.position.price}")
        else:
            order = self.sell()
            print(f"====submit sell order, date: {self.datas[0].datetime.date(0)},size:{order.size},position:{self.position.size}*{self.position.price}={self.position.size*self.position.price}")

    def notify_order(self, order):
        # print(f"submit:{order.Submitted}, Accepted:{order.Accepted}, Completed:{order.Completed}, Canceled:{order.Canceled}, Rejected:{order.Rejected},Margin:{order.Margin},Partial:{order.Partial}")
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order.isbuy():
                print(f"****date: {self.datas[0].datetime.date(0)},Buy executed, price: {order.executed.price}, cost: {order.executed.value}, commission: {order.executed.comm},status:{order.status},size:{order.size},position:{self.position.size}*{self.position.price}={self.position.size*self.position.price}")
            elif order.issell():
                print(f"====date: {self.datas[0].datetime.date(0)},Sell executed, price: {order.executed.price}, cost: {order.executed.value}, commission: {order.executed.comm},status:{order.status},size:{order.size},position:{self.position.size}*{self.position.price}={self.position.size*self.position.price}")
        
            self.order = None

    def notify_trade(self, trade):
        
        print(f"Trade closed, profit: {trade.pnlcomm}")
        print(self.position)