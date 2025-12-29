import logging
import os
from pprint import pformat
import sys
# 安装了 gymnasium 后，先导入它
import gymnasium as gym
# 将 "gym" 模块名映射到 gymnasium 实例
sys.modules["gym"] = gym

import qlib
from qlib.data import D
from qlib.utils import init_instance_by_config
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, SigAnaRecord
from qlib.contrib.workflow.record_temp import SignalMseRecord, MultiSegRecord

# -----------------------------
# 全局日志设置
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("qlib-workflow-by-code")

# -----------------------------
# 参数：数据目录与时间段
# -----------------------------
# 获取当前文件目录
# -----------------------------
# 获取当前文件目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#获取父路径
parent_dir = os.path.dirname(current_dir)
# 构建 qlib_data/cn_data 的路径
PROVIDER_URI = os.path.join(parent_dir, "qlib_data/cn_data")  # 请根据你的本地路径调整
REGION = "cn"
POOL = "csi300"  # 股票池
FREQ = "day"

# 统一时间段（数据覆盖）
START_TIME = "2010-01-01"
END_TIME = "2022-12-31"

# 训练/验证/测试拆分
SEGMENTS = {
    "train": ("2010-01-01", "2017-12-31"),
    "valid": ("2018-01-01", "2018-12-31"),
    "test":  ("2019-01-01", "2020-12-31"),
}

# -----------------------------
# 1. 数据准备：从原始数据构造特征与标签
# -----------------------------
# 说明：
# - 采用 qlib 的特征表达式 DSL，从行情原始字段构造特征
# - 标签选择“下一日收益率”：Ref($close, -1)/$close - 1
# - 特征工程包含：收益率、振幅、滚动均值/标准差等

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

def preview_raw_features_and_label():
    """演示如何直接从原始数据生成 features/labels（便于理解机制）"""
    instruments = D.instruments(POOL)
    logger.info("Instruments pool: %s", POOL)
    # 取一个较小的样本做预览（例如前20只）
    inst_list = D.list_instruments(instruments, start_time=START_TIME, end_time=END_TIME, as_list=True)[:20]
    logger.info("Preview instruments: %s ...", inst_list[:5])

    # 直接用 D.features 从原始数据计算特征与标签（MultiIndex: instrument, datetime）
    df_features = D.features(inst_list, feature_exprs, start_time=SEGMENTS["train"][0], end_time=SEGMENTS["train"][1], freq=FREQ)
    df_labels = D.features(inst_list, label_exprs, start_time=SEGMENTS["train"][0], end_time=SEGMENTS["train"][1], freq=FREQ)

    df_features.columns = feature_names
    df_labels.columns = label_names

    logger.info("Raw feature sample:\n%s", pformat(df_features.head(10)))
    logger.info("Raw label sample:\n%s", pformat(df_labels.head(10)))
    logger.info("Shapes | features: %s | labels: %s", df_features.shape, df_labels.shape)

# -----------------------------
# 2. 构建 Dataset（纯 Python 字典，不用配置文件）
# -----------------------------
# 说明：
# - 使用 DataHandlerLP + QlibDataLoader，传入自定义表达式与列名
# - infer_processors 用于推理期/训练前的特征规范化与填充
# - learn_processors 用于学习期的数据清洗与标签归一（可根据需要调整）

DATASET_CONFIG = {
    "class": "DatasetH",
    "module_path": "qlib.data.dataset",
    "kwargs": {
        "handler": {
            "class": "DataHandlerLP",
            "module_path": "qlib.data.dataset.handler",
            "kwargs": {
                "instruments": POOL,
                "start_time": START_TIME,
                "end_time": END_TIME,
                "data_loader": {
                    "class": "QlibDataLoader",
                    "module_path": "qlib.data.dataset.loader",
                    "kwargs": {
                        "config": {
                            # 自定义特征表达式与列名
                            "feature": [feature_exprs, feature_names],
                            # 自定义标签表达式与列名
                            "label": [label_exprs, label_names],
                        }
                        ,
                        "freq": FREQ
                    },
                },
                # 特征工程（推理期处理）
                "infer_processors": [
                    {"class": "RobustZScoreNorm", "module_path": "qlib.data.dataset.processor", "kwargs": {"fields_group": "feature", "clip_outlier": True, "fit_start_time": SEGMENTS["train"][0], "fit_end_time": SEGMENTS["train"][1]}},
                    {"class": "Fillna", "module_path": "qlib.data.dataset.processor", "kwargs": {"fields_group": "feature"}},
                    {"class": "Fillna", "module_path": "qlib.data.dataset.processor", "kwargs": {"fields_group": "label"}},
                ],
                # 训练期清洗/规范化
                "learn_processors": [
                    {"class": "DropnaLabel", "module_path": "qlib.data.dataset.processor"},
                    {"class": "CSRankNorm", "module_path": "qlib.data.dataset.processor", "kwargs": {"fields_group": "label"}},
                ],
            },
        },
        # 训练/验证/测试拆分
        "segments": SEGMENTS,
    },
}

# -----------------------------
# 3. 定义模型（LightGBM）
# -----------------------------
# 说明：
# - 选择 qlib 的 LGBModel 并设定常见超参数
# - 可根据需要更改 n_estimators/num_leaves/learning_rate 等

MODEL_CONFIG = {
    "class": "LGBModel",
    "module_path": "qlib.contrib.model.gbdt",
    "kwargs": {
        "loss": "mse",
        "learning_rate": 0.05,
        "n_estimators": 800,
        "num_leaves": 64,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 1.0,
        "reg_lambda": 1.0,
        "min_child_samples": 20,
        "verbosity": -1,
        # 允许在 fit 时传入 evals_result 收集验证集指标
    },
}

# -----------------------------
# 4. 训练过程与监控
# -----------------------------
def run_training_and_evaluation():
    # 初始化 qlib（只需一次）
    qlib.init(provider_uri=PROVIDER_URI, region=REGION)
    logger.info("qlib initialized: provider_uri=%s region=%s", PROVIDER_URI, REGION)

    # 数据预览（理解特征/标签从原始数据生成）
    preview_raw_features_and_label()

    # 实例化数据集与模型（纯 Python 字典）
    dataset = init_instance_by_config(DATASET_CONFIG)
    model = init_instance_by_config(MODEL_CONFIG)

    # 启动实验记录器（无需外部配置），记录参数与训练指标
    with R.start(experiment_name="by_code_lgbm_workflow"):
        recorder = R.get_recorder()
        # 记录数据与模型配置参数
        R.log_params(dataset=DATASET_CONFIG, model=MODEL_CONFIG)

        logger.info("Start training LGBModel ...")
        evals_result = dict()
        # 训练：内部将自动使用 DatasetH 的 train 段，并在 valid 段上评估
        model.fit(dataset, evals_result=evals_result)
        logger.info("Training done. Valid eval results (loss curve length=%d)", len(evals_result.get("valid", [])))

        # 将验证集损失曲线写入记录器
        if "valid" in evals_result:
            v = evals_result["valid"]
            if isinstance(v, (list, tuple)):
                last = v[-1]
            elif isinstance(v, dict):
                k = next(iter(v))
                seq = v[k]
                last = seq[-1] if isinstance(seq, (list, tuple)) else seq
            else:
                last = v
            R.log_metrics(valid_last=float(last))
        v = evals_result.get("valid", [])
        sample = v[:10] if isinstance(v, (list, tuple)) else (list(v.items())[:1] if isinstance(v, dict) else v)
        logger.info("Valid loss sample (first 10): %s", sample)

        # 生成预测与标签、并计算 IC/Rank IC
        SignalRecord(model, dataset, recorder).generate()
        SigAnaRecord(recorder, ana_long_short=False, ann_scaler=252).generate()

        # 计算 MSE/RMSE
        SignalMseRecord(recorder).generate()

        # 多分段评估（valid & test）
        MultiSegRecord(model, dataset, recorder).generate(
            segments={"valid": "valid", "test": "test"},
            save=True
        )

        logger.info("All evaluation records generated. Check metrics and artifacts in recorder.")
        logger.info("Experiment ID: %s", recorder.id)

if __name__ == "__main__":
    run_training_and_evaluation()
