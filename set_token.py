#!/usr/bin/env python3
"""
Tushare Token 设置工具
用于安全地设置TUSHARE_TOKEN环境变量
"""
import os
import subprocess
import sys

def set_token():
    print("=== Tushare Token 设置工具 ===")
    print("请输入您的Tushare API Token:")
    print("(Token可以从 https://tushare.pro/user/token 获取)")
    
    # 获取用户输入的token
    token = input("请输入Token: ").strip()
    
    if not token:
        print("错误: Token不能为空")
        return False
    
    if len(token) < 20:  # 基本验证token长度
        print("警告: Token长度可能不正确，请确认")
        confirm = input("是否继续? (y/N): ").strip().lower()
        if confirm != 'y':
            return False
    
    # 检测当前shell类型
    shell = os.getenv('SHELL', '/bin/bash')
    
    # 写入到.env文件
    env_file = '.env'
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(f"TUSHARE_TOKEN={token}\n")
        print(f"✓ Token已保存到 {env_file} 文件")
    except Exception as e:
        print(f"错误: 无法写入.env文件: {e}")
        return False
    
    # 设置当前环境变量
    os.environ['TUSHARE_TOKEN'] = token
    print("✓ 当前会话环境变量已设置")
    
    # 提供永久设置的建议
    print("\n=== 永久设置方法 ===")
    if 'zsh' in shell:
        config_file = '~/.zshrc'
    elif 'bash' in shell:
        config_file = '~/.bashrc 或 ~/.bash_profile'
    else:
        config_file = '您的shell配置文件'
    
    print(f"要永久设置环境变量，请将以下内容添加到 {config_file}:")
    print(f"export TUSHARE_TOKEN='{token}'")
    print("\n或者每次运行前执行:")
    print("source .env  # 如果您的shell支持")
    
    return True

def load_from_env():
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

if __name__ == '__main__':
    # 首先尝试从.env文件加载
    if load_from_env():
        existing_token = os.getenv('TUSHARE_TOKEN')
        if existing_token:
            print("发现现有Token配置")
            use_existing = input("是否使用现有Token? (Y/n): ").strip().lower()
            if use_existing != 'n':
                print("✓ 使用现有Token")
                sys.exit(0)
    
    # 设置新token
    if set_token():
        print("\n✓ Token设置完成！")
        print("现在可以运行: python3 main.py")
    else:
        print("✗ Token设置失败")
        sys.exit(1)
