"""
邮件发送工具
支持SMTP邮件发送功能，用于密码重置等场景
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import os
from src.utils.logger import logger


def check_smtp_configured():
    """检查SMTP是否已配置"""
    smtp_server = os.getenv('SMTP_SERVER', '').strip()
    smtp_username = os.getenv('SMTP_USERNAME', '').strip()
    smtp_password = os.getenv('SMTP_PASSWORD', '').strip()
    
    # 检查是否为默认示例配置
    if smtp_server in ['', 'smtp.example.com']:
        return False
    if smtp_username in ['', 'your-email@example.com']:
        return False
    if smtp_password in ['', 'your-smtp-password']:
        return False
    
    return True


def send_email(to_email, subject, html_content, text_content=None):
    """
    发送HTML邮件
    
    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        html_content: HTML格式邮件内容
        text_content: 纯文本格式邮件内容（可选，用于不支持HTML的邮件客户端）
    
    Returns:
        (success, error_message)
    """
    # 检查SMTP配置
    if not check_smtp_configured():
        logger.error("SMTP未配置或配置不完整，无法发送邮件")
        return False, "SMTP服务未配置"
    
    try:
        # 读取SMTP配置
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_name = os.getenv('SMTP_FROM_NAME', 'AICouncil')
        from_email = os.getenv('SMTP_FROM_EMAIL', smtp_username)
        
        # 创建邮件对象
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 添加纯文本部分（如果提供）
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)
        
        # 添加HTML部分
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 连接SMTP服务器并发送
        if smtp_use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        
        server.login(smtp_username, smtp_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        
        logger.info(f"✅ 邮件发送成功: {to_email} - {subject}")
        return True, None
        
    except Exception as e:
        error_msg = f"邮件发送失败: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def send_password_reset_email(user_email, username, reset_link):
    """
    发送密码重置邮件
    
    Args:
        user_email: 用户邮箱
        username: 用户名
        reset_link: 密码重置链接（包含token）
    
    Returns:
        (success, error_message)
    """
    subject = "AICouncil - 密码重置请求"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                color: white;
                margin: 0;
                font-size: 24px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white !important;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .footer {{
                padding: 20px 30px;
                background: #f8f9fa;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
            .warning {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏛️ AICouncil 密码重置</h1>
            </div>
            <div class="content">
                <p>您好，<strong>{username}</strong>：</p>
                <p>我们收到了您的密码重置请求。点击下方按钮重置您的密码：</p>
                <div style="text-align: center;">
                    <a href="{reset_link}" class="button">重置密码</a>
                </div>
                <p style="font-size: 14px; color: #666;">
                    或者复制以下链接到浏览器打开：<br>
                    <a href="{reset_link}" style="color: #667eea; word-break: break-all;">{reset_link}</a>
                </p>
                <div class="warning">
                    <strong>⚠️ 安全提示：</strong>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>此链接30分钟内有效，仅可使用一次</li>
                        <li>如果您没有请求重置密码，请忽略此邮件</li>
                        <li>请勿将此链接分享给任何人</li>
                    </ul>
                </div>
            </div>
            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复。</p>
                <p>© 2026 AICouncil. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
AICouncil - 密码重置请求

您好，{username}：

我们收到了您的密码重置请求。请访问以下链接重置您的密码：

{reset_link}

安全提示：
- 此链接30分钟内有效，仅可使用一次
- 如果您没有请求重置密码，请忽略此邮件
- 请勿将此链接分享给任何人

此邮件由系统自动发送，请勿直接回复。

© 2026 AICouncil. All rights reserved.
    """
    
    return send_email(user_email, subject, html_content, text_content)
