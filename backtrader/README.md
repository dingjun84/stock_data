https://www.heywhale.com/mw/project/63857587d0329ee911dcd7f2
https://www.poloxue.com/backtrader/docs/01-introduction/

# 基本概念
天基本的数据，卖出和买入都是提交订单后第二天的收盘价

# 策略中可以引入broker
    - 获取当前可用现金
    ```
    cash = self.broker.get_cash()
    ```
    
    - 获取当前持仓的总价值（股票市值+现金）
    ```
    value = self.broker.get_value()
    ```