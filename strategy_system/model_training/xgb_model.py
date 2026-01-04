import xgboost as xgb
import joblib
import numpy as np
import os

class XGBModel:
    """
    XGBoost模型类，负责训练、加载和预测
    """
    def __init__(self, model_path=None):
        """
        初始化XGBModel
        :param model_path: 模型保存路径
        """
        self.model = None
        self.model_path = model_path
    
    def train(self, X, y, model_path=None, incremental=False, num_boost_round=100):
        """
        训练或增量训练XGBoost模型并保存
        :param X: 特征数据
        :param y: 标签数据
        :param model_path: 模型保存路径（可选，优先使用实例化时的路径）
        :param incremental: 是否增量训练
        :param num_boost_round: 增量训练时的提升轮数
        :return: 训练好的模型
        """
        print("开始训练XGBoost模型...")
        
        # 使用实例化路径或传入的路径
        save_path = model_path or self.model_path
        if not save_path:
            raise ValueError("请指定模型保存路径")
        
        if incremental:
            print("进行增量训练...")
            # 加载已有模型
            if self.model is None:
                try:
                    self.load(save_path)
                except FileNotFoundError:
                    print("未找到已有模型，进行初次训练...")
                    incremental = False
            
            if incremental and self.model is not None:
                # 增量训练
                # 获取当前模型的参数
                params = self.model.get_params()
                
                # 设置增量训练的参数
                params['n_estimators'] += num_boost_round
                params['learning_rate'] = 0.02  # 可以调整增量训练的学习率
                
                print(f"在原有模型基础上增加 {num_boost_round} 棵树，总树数: {params['n_estimators']}")
                
                # 创建新模型，使用相同参数但增加树的数量
                model = xgb.XGBRegressor(**params)
                
                # 使用warm_start=True进行增量训练
                model.warm_start = True
                model.fit(X, y, xgb_model=self.model)
        
        if not incremental:
            # 初次训练
            model = xgb.XGBRegressor(
                objective='reg:squarederror',
                max_depth=5,
                n_estimators=300,
                learning_rate=0.02,
                subsample=0.7,
                colsample_bytree=0.7,
                random_state=42
            )
            model.fit(X, y)
        
        # 创建模型保存目录
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 保存模型
        joblib.dump(model, save_path)
        print(f"模型已保存到: {save_path}")
        
        # 打印特征重要性
        print("\n特征重要性:")
        for i, col in enumerate(X.columns):
            print(f"{col}: {model.feature_importances_[i]:.4f}")
        
        self.model = model
        return model
    
    def load(self, model_path=None):
        """
        加载XGBoost模型
        :param model_path: 模型保存路径（可选，优先使用实例化时的路径）
        :return: 加载的模型
        """
        load_path = model_path or self.model_path
        if not load_path:
            raise ValueError("请指定模型加载路径")
        
        print(f"从{load_path}加载XGBoost模型...")
        model = joblib.load(load_path)
        print("模型加载完成")
        
        self.model = model
        return model
    
    def predict(self, df, feature_cols):
        """
        使用模型预测并生成score
        :param df: 特征数据
        :param feature_cols: 特征列名列表
        :return: 包含score的DataFrame
        """
        if self.model is None:
            raise ValueError("模型未加载，请先调用load或train方法")
        
        df = df.copy()
        # 只对有完整特征的数据进行预测
        valid_mask = df[feature_cols].notna().all(axis=1)
        df.loc[valid_mask, 'score'] = self.model.predict(df[valid_mask][feature_cols])
        df.loc[~valid_mask, 'score'] = np.nan
        return df