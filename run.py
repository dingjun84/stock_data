#!/usr/bin/env python3
"""
股票数据获取程序启动器
自动检查和设置环境变量，然后运行main.py
"""
import os
import sys
import subprocess

def load_env_file():
    """从.env文件加载环境变量"""
    env_file = '.env'
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            return True
        except Exception as e:
            print(f"读取.env文件失败: {e}")
            return False
    return False

def check_token():
    """检查TUSHARE_TOKEN是否已设置"""
    # 先从.env文件加载
    load_env_file()
    
    token = os.getenv('TUSHARE_TOKEN')
    if token and len(token) > 10:  # 基本验证
        return True
    return False

def main():
    print("=== 股票数据获取程序 ===")
    
    # 检查token
    if not check_token():
        print("未检测到TUSHARE_TOKEN环境变量")
        print("正在启动token设置工具...")
        
        # 运行token设置工具
        try:
            result = subprocess.run([sys.executable, 'set_token.py'], check=True)
        except subprocess.CalledProcessError:
            print("Token设置失败，程序退出")
            sys.exit(1)
        except FileNotFoundError:
            print("错误: 找不到set_token.py文件")
            sys.exit(1)
        
        # 重新检查token
        if not check_token():
            print("Token设置后仍然无效，程序退出")
            sys.exit(1)
    
    print("✓ TUSHARE_TOKEN 已配置")
    print("启动股票数据获取程序...")
    print("-" * 50)
    
    # 运行主程序
    try:
        subprocess.run([sys.executable, 'main.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"主程序执行失败: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("错误: 找不到main.py文件")
        sys.exit(1)

if __name__ == '__main__':
    main()
