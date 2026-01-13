#!/usr/bin/env python3
"""
环境配置验证脚本
检查所有必需的环境变量是否正确配置
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 定义配置项及其验证规则
CONFIG_CHECKS = {
    # 必需项（生产环境）
    'SECRET_KEY': {
        'required': True,
        'production_only': True,
        'min_length': 32,
        'default_values': ['your-secret-key-here-please-change-this-in-production', 'dev-secret-key-please-change-in-production'],
        'description': 'Flask密钥（用于session加密）',
        'generate_cmd': 'flask generate-secret-key'
    },
    
    # 数据库配置
    'DATABASE_URL': {
        'required': False,
        'default': 'sqlite:///data/users.db',
        'description': '数据库连接URI'
    },
    
    # 环境配置
    'FLASK_ENV': {
        'required': False,
        'default': 'development',
        'valid_values': ['development', 'production'],
        'description': 'Flask运行环境'
    },
    
    # 注册配置
    'ALLOW_PUBLIC_REGISTRATION': {
        'required': False,
        'default': 'false',
        'valid_values': ['true', 'false'],
        'description': '是否允许公开注册'
    },
    
    # Session配置
    'PERMANENT_SESSION_LIFETIME': {
        'required': False,
        'default': '2592000',
        'type': 'int',
        'min_value': 3600,
        'description': 'Session超时时间（秒）'
    },
    
    'SESSION_COOKIE_SECURE': {
        'required': False,
        'default': 'false',
        'production_recommended': 'true',
        'description': '是否强制HTTPS传输cookie'
    },
    
    # 安全配置
    'ACCOUNT_LOCKOUT_THRESHOLD': {
        'required': False,
        'default': '5',
        'type': 'int',
        'description': '账户锁定阈值（登录失败次数）'
    },
    
    'ACCOUNT_LOCKOUT_DURATION': {
        'required': False,
        'default': '300',
        'type': 'int',
        'description': '账户锁定时长（秒）'
    },
    
    'MFA_TIMEOUT': {
        'required': False,
        'default': '600',
        'type': 'int',
        'description': 'MFA验证超时时间（秒）'
    },
    
    # 密码策略
    'PASSWORD_MIN_LENGTH': {
        'required': False,
        'default': '8',
        'type': 'int',
        'min_value': 6,
        'description': '密码最小长度'
    },
}

# ANSI颜色代码
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_status(status, message):
    """打印带颜色的状态消息"""
    if status == 'ok':
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")
    elif status == 'warning':
        print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")
    elif status == 'error':
        print(f"{Colors.RED}✗{Colors.RESET} {message}")
    elif status == 'info':
        print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")

def validate_config():
    """验证配置"""
    is_production = os.getenv('FLASK_ENV') == 'production'
    errors = []
    warnings = []
    
    print(f"\n{'='*60}")
    print(f"AICouncil 环境配置验证")
    print(f"{'='*60}\n")
    
    print_status('info', f"环境: {Colors.BLUE}{os.getenv('FLASK_ENV', 'development')}{Colors.RESET}")
    print_status('info', f".env文件: {Colors.BLUE}{Path('.env').absolute()}{Colors.RESET}")
    print()
    
    # 检查每个配置项
    for key, rules in CONFIG_CHECKS.items():
        value = os.getenv(key)
        
        # 检查必需项
        if rules.get('required') or (is_production and rules.get('production_only')):
            if not value:
                error_msg = f"{key}: 未设置（必需）"
                errors.append(error_msg)
                print_status('error', error_msg)
                if rules.get('generate_cmd'):
                    print(f"  {Colors.YELLOW}生成命令: {rules['generate_cmd']}{Colors.RESET}")
                continue
        
        # 如果未设置，使用默认值
        if not value:
            value = rules.get('default')
            if value:
                print_status('info', f"{key}: 使用默认值 ({value})")
            continue
        
        # 检查默认值（生产环境不应使用默认密钥）
        if is_production and 'default_values' in rules:
            if value in rules['default_values']:
                error_msg = f"{key}: 仍在使用默认值（生产环境不安全）"
                errors.append(error_msg)
                print_status('error', error_msg)
                continue
        
        # 检查最小长度
        if 'min_length' in rules and len(value) < rules['min_length']:
            error_msg = f"{key}: 长度不足（当前{len(value)}，要求>={rules['min_length']}）"
            errors.append(error_msg)
            print_status('error', error_msg)
            continue
        
        # 检查有效值
        if 'valid_values' in rules and value.lower() not in rules['valid_values']:
            error_msg = f"{key}: 无效值 '{value}'（有效值: {', '.join(rules['valid_values'])}）"
            errors.append(error_msg)
            print_status('error', error_msg)
            continue
        
        # 检查类型
        if rules.get('type') == 'int':
            try:
                int_value = int(value)
                if 'min_value' in rules and int_value < rules['min_value']:
                    warning_msg = f"{key}: 值过小（当前{int_value}，建议>={rules['min_value']}）"
                    warnings.append(warning_msg)
                    print_status('warning', warning_msg)
            except ValueError:
                error_msg = f"{key}: 必须为整数（当前: {value}）"
                errors.append(error_msg)
                print_status('error', error_msg)
                continue
        
        # 生产环境推荐值
        if is_production and 'production_recommended' in rules:
            if value.lower() != rules['production_recommended']:
                warning_msg = f"{key}: 生产环境建议设置为 {rules['production_recommended']}（当前: {value}）"
                warnings.append(warning_msg)
                print_status('warning', warning_msg)
                continue
        
        # 配置正常
        print_status('ok', f"{key}: {value}")
    
    # 检查.env文件是否存在
    print()
    if not Path('.env').exists():
        warning_msg = ".env文件不存在，请从.env.example复制并修改"
        warnings.append(warning_msg)
        print_status('warning', warning_msg)
        print(f"  {Colors.YELLOW}命令: cp .env.example .env{Colors.RESET}")
    
    # 总结
    print(f"\n{'='*60}")
    if errors:
        print_status('error', f"发现 {len(errors)} 个错误")
        for err in errors:
            print(f"  - {err}")
    
    if warnings:
        print_status('warning', f"发现 {len(warnings)} 个警告")
        for warn in warnings:
            print(f"  - {warn}")
    
    if not errors and not warnings:
        print_status('ok', "所有配置项验证通过！")
    
    print(f"{'='*60}\n")
    
    return len(errors) == 0

if __name__ == '__main__':
    success = validate_config()
    sys.exit(0 if success else 1)
