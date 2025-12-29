import sys
# 安装了 gymnasium 后，先导入它
import gymnasium as gym

from qlib.data.dataset import DatasetH
# 将 "gym" 模块名映射到 gymnasium 实例
sys.modules["gym"] = gym

import qlib
from qlib.data.dataset.loader import QlibDataLoader
from qlib.data.dataset.handler import DataHandlerLP


def gen_feature_label():
    MACD_EXP = '(EMA($close, 12) - EMA($close, 26))/$close - EMA((EMA($close, 12) - EMA($close, 26))/$close, 9)/$close'
    fields = [MACD_EXP,'Ref($close, -2)','Ref($close, -1)','$close','$factor'] # MACD
    names = ['MACD', 'Ref($close, -2)','Ref($close, -1)','$close','$factor'] 
    labels = ['Ref($close, -2)/Ref($close, -1) - 1'] # label
    label_names = ['LABEL']
    data_loader_config = {
        "feature": (fields, names),
        "label": (labels, label_names)
    }
    data_loader = QlibDataLoader(config=data_loader_config)
    # instrument: csi300
    # instrument:  ['SH600000']
    df = data_loader.load(instruments= ['SH600000'], start_time='2020-01-01', end_time='2020-01-31')
    print(df)


def handle_dataset():
    feature_exprs = [
        # 当日收益率（相对前一日）
        "$close/Ref($close, 1) - 1",
        # 振幅（高低价相对开盘）
        "($high - $low)/$open",
        # 5日滚动均值（基于日收益率）
        "Mean($close/Ref($close, 1) - 1, 5)",
        # 10日滚动标准差（基于日收益率）
        "Std($close/Ref($close, 1) - 1, 10)",
        # 成交量变化率
        "$volume/Ref($volume, 1) - 1",
    ]
    feature_names = ["RET1", "RANGE_OPEN", "RET_MEAN_5", "RET_STD_10", "VOL_CHG"]

    # 下一日收益标签：负号表示“未来期”，参见 qlib 的 Ref 语义
    label_exprs = ["Ref($close, -1)/$close - 1"]
    label_names = ["LABEL_NEXT_RET"]
    data_loader_config = {
        "feature": (feature_exprs, feature_names),
        "label": (label_exprs, label_names)
    }
    data_loader = QlibDataLoader(config=data_loader_config)
    data_handler = DataHandlerLP(instruments=['SH600000'],start_time='2010-01-01', end_time='2020-01-31',data_loader=data_loader)
    df = data_handler.fetch(("2010-01-01", "2017-12-31"))
    print(df)

def dataset_test():
    DatasetH
    # __init__() -> setup_data() -> handler.setup_data

    # Model.fit() -> _prepare_data() -> 
    # key in ["train", "valid"]
    # df = dataset.prepare(key, col_set=["feature", "label"], data_key=DataHandlerLP.DK_L)
    
if __name__ == "__main__":
    qlib.init(provider_uri="./qlib_data/cn_data")
    # gen_feature_label()
    handle_dataset()