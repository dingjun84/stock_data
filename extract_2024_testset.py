import pandas as pd
import os

# 定义文件路径
input_file = './stock_data/feature_label/stock_feature_label_2024_testset.csv'
output_file = './stock_data/feature_label/stock_feature_label_2024_12_testset.csv'

# 创建输出目录
os.makedirs(os.path.dirname(output_file), exist_ok=True)

print("开始提取2024年12月测试集数据...")

# 读取文件并提取2024年数据
# 使用chunksize分块读取，处理大数据文件
chunksize = 100000
processed_chunks = 0

# 第一次遍历，计算总样本数
print("计算总样本数...")
total_2024_samples = 0
for chunk in pd.read_csv(input_file, chunksize=chunksize):
    # 提取trade_date以'2024'开头的数据
    chunk_2024 = chunk[chunk['trade_date'].astype(str).str.startswith('202412')]
    total_2024_samples += len(chunk_2024)
    processed_chunks += 1
    print(f"已处理 {processed_chunks * chunksize:,} 行，发现 2024 年12月样本 {total_2024_samples:,} 个")

print(f"\n2024年12月总样本数: {total_2024_samples:,}")
print("开始写入2024年12月测试集文件...")    

# 第二次遍历，写入2024年数据
first_chunk = True
processed_chunks = 0
written_samples = 0

for chunk in pd.read_csv(input_file, chunksize=chunksize):
    # 提取trade_date以'2024'开头的数据
    chunk_2024 = chunk[chunk['trade_date'].astype(str).str.startswith('202412')]
    
    if len(chunk_2024) > 0:
        # 写入文件，第一次写入时包含表头
        chunk_2024.to_csv(
            output_file,
            mode='w' if first_chunk else 'a',
            header=first_chunk,
            index=False
        )
        
        first_chunk = False
        written_samples += len(chunk_2024)
    
    processed_chunks += 1
    print(f"已处理 {processed_chunks * chunksize:,} 行，已写入 2024 年样本 {written_samples:,} 个")
    
    # 进度显示
    if total_2024_samples > 0:
        progress = (written_samples / total_2024_samples) * 100
        print(f"进度: {progress:.2f}%")

print(f"\n2024年12 月测试集提取完成！")
print(f"输出文件: {output_file}")
print(f"写入样本数: {written_samples:,}")

# 验证输出文件
print("\n验证输出文件...")
df_test = pd.read_csv(output_file)
print(f"验证结果: 文件包含 {len(df_test):,} 个样本")
print(f"日期范围: {df_test['trade_date'].min()} 到 {df_test['trade_date'].max()}")
