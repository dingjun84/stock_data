# 股票数据获取程序

基于Tushare API的股票历史数据批量获取工具，支持增量更新和大数据量处理。

## 功能特性

- ✅ 批量获取股票历史数据
- ✅ 突破API 6000条数据限制，自动分批拉取
- ✅ 增量更新：跳过已完整的数据，只更新缺失部分
- ✅ 智能处理：每次只处理指定数量的需要更新的股票
- ✅ 安全token管理：使用环境变量存储API密钥
- ✅ 错误处理和重试机制

## 快速开始

### 1. 安装依赖

```bash
pip install tushare pandas
```

### 2. 获取Tushare API Token

访问 [Tushare官网](https://tushare.pro/user/token) 获取您的API Token

### 3. 运行程序

**方式一：使用启动器（推荐）**
```bash
python3 run.py
```
第一次运行会自动引导您设置token。

**方式二：手动设置环境变量**
```bash
# 设置token
python3 set_token.py

# 运行主程序
python3 main.py
```

**方式三：直接设置环境变量**
```bash
export TUSHARE_TOKEN='your_token_here'
python3 main.py
```

## 文件说明

- `main.py` - 主程序，股票数据获取逻辑
- `run.py` - 启动器，自动检查环境并运行主程序
- `set_token.py` - Token设置工具
- `tushare_stock_basic_*.csv` - 股票基础信息文件
- `.env` - 环境变量文件（自动生成，包含敏感信息）

## 配置参数

在 `main.py` 中可以调整以下参数：

```python
max_stocks = 2  # 每次执行最多处理的股票数量
end_date = '20251010'  # 数据结束日期
```

## 运行逻辑

1. 读取股票基础信息CSV文件
2. 检查每只股票的现有数据文件
3. 跳过数据已完整的股票
4. 对需要更新的股票进行分批拉取
5. 处理达到 `max_stocks` 限制后停止
6. 下次运行继续处理剩余股票

## 输出文件

每只股票生成独立的CSV文件，保存在`stock_data/`目录下：
- 目录：`stock_data/`
- 文件名格式：`stock_data_{股票代码}.csv`
- 包含完整的历史交易数据
- 按日期排序（从早到晚）

程序会自动创建`stock_data/`目录（如果不存在）。

## 注意事项

- Token信息存储在 `.env` 文件中，已添加到 `.gitignore`
- 建议设置合理的 `max_stocks` 值避免API频率限制
- 程序会自动添加延时以防止触发API限制
- 支持断点续传，可随时中断和恢复

## 安全性

- ✅ Token不会硬编码在源代码中
- ✅ `.env` 文件已加入 `.gitignore`
- ✅ 支持从环境变量读取token
- ✅ 提供安全的token设置工具
