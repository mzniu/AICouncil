# 生产环境部署指南

本文档提供AICouncil应用在生产环境中的完整部署指南，包括环境配置、安全设置、反向代理、进程管理等。

## 📋 前置要求

- Python 3.10+
- PostgreSQL 12+ 或 MySQL 8.0+（推荐）或 SQLite（仅开发）
- Nginx 或 Apache（反向代理）
- SSL证书（Let's Encrypt推荐）
- 2GB+ RAM
- 10GB+ 磁盘空间

## 🚀 快速部署

### 1. 克隆项目并安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd MyCouncil

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器（PDF导出功能）
playwright install chromium
```

### 2. 环境配置

#### 复制环境变量模板
```bash
cp .env.example .env
```

#### 生成SECRET_KEY（必需）

**方法1：使用Flask CLI**
```bash
flask generate-secret-key
```

**方法2：使用Python**
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

将生成的密钥添加到`.env`：
```ini
SECRET_KEY=<your-generated-random-key-at-least-32-bytes>
FLASK_ENV=production
```

#### 完整生产环境配置示例

编辑`.env`文件：

```ini
# ========================================
# Flask 应用配置
# ========================================
SECRET_KEY=<your-generated-secret-key>
FLASK_ENV=production
FLASK_DEBUG=false

# ========================================
# 数据库配置（推荐PostgreSQL）
# ========================================
DATABASE_URL=postgresql://aicouncil_user:secure_password@localhost:5432/aicouncil

# ========================================
# Session配置
# ========================================
PERMANENT_SESSION_LIFETIME=2592000
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# ========================================
# 认证安全配置
# ========================================
ALLOW_PUBLIC_REGISTRATION=false
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_DURATION=300
MFA_TIMEOUT=600

# 密码策略
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true

# ========================================
# 日志配置
# ========================================
LOG_LEVEL=WARNING
LOG_FILE=/var/log/aicouncil/app.log
```

### 3. 数据库初始化

#### PostgreSQL数据库创建

```bash
# 登录PostgreSQL
sudo -u postgres psql

# 创建数据库和用户
CREATE DATABASE aicouncil;
CREATE USER aicouncil_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE aicouncil TO aicouncil_user;
\q
```

#### 运行数据库迁移

```bash
# 初始化迁移
flask db init

# 生成迁移脚本
flask db migrate -m "Initial migration"

# 应用迁移
flask db upgrade
```

#### 创建管理员账户

```bash
flask create-admin
# 按提示输入：
# - 用户名
# - 密码（满足策略要求）
# - 邮箱
```

### 4. 验证配置

运行配置验证脚本：
```bash
python scripts/validate_env.py
```

验证内容包括：
- ✅ SECRET_KEY长度是否足够（≥32字节）
- ✅ 生产环境是否使用了默认值
- ✅ 密码策略配置是否合理
- ✅ Session安全配置是否启用

### 5. 反向代理配置

#### Nginx配置

创建配置文件 `/etc/nginx/sites-available/aicouncil`：

```nginx
# HTTP重定向到HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 请求体大小限制
    client_max_body_size 10M;
    
    # 代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
    
    # 静态文件缓存
    location /static {
        alias /var/www/aicouncil/src/web/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

启用配置并重启Nginx：
```bash
sudo ln -s /etc/nginx/sites-available/aicouncil /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 获取SSL证书（Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 6. 进程管理（使用Gunicorn + systemd）

#### 安装Gunicorn

```bash
pip install gunicorn
```

#### 创建systemd服务

创建文件 `/etc/systemd/system/aicouncil.service`：

```ini
[Unit]
Description=AICouncil Application
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/aicouncil
Environment="PATH=/var/www/aicouncil/venv/bin"

# Gunicorn配置
ExecStart=/var/www/aicouncil/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 300 \
    --access-logfile /var/log/aicouncil/access.log \
    --error-logfile /var/log/aicouncil/error.log \
    "src.web.app:app"

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGQUIT
TimeoutStopSec=5

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 启动服务

```bash
# 创建日志目录
sudo mkdir -p /var/log/aicouncil
sudo chown www-data:www-data /var/log/aicouncil

# 重载systemd配置
sudo systemctl daemon-reload

# 启用并启动服务
sudo systemctl enable aicouncil
sudo systemctl start aicouncil

# 检查状态
sudo systemctl status aicouncil
```

### 7. 日志管理

#### 日志轮转配置

创建文件 `/etc/logrotate.d/aicouncil`：

```
/var/log/aicouncil/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload aicouncil > /dev/null 2>&1 || true
    endscript
}
```

### 8. 数据库备份

#### 创建备份脚本

创建文件 `scripts/backup_db.sh`：

```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/aicouncil"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="aicouncil"
DB_USER="aicouncil_user"

mkdir -p "$BACKUP_DIR"

# 备份PostgreSQL数据库
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/aicouncil_$TIMESTAMP.sql.gz"

# 保留最近30天的备份
find "$BACKUP_DIR" -name "aicouncil_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/aicouncil_$TIMESTAMP.sql.gz"
```

设置执行权限：
```bash
chmod +x scripts/backup_db.sh
```

#### 设置定时备份

```bash
crontab -e
# 添加：每天凌晨2点备份数据库
0 2 * * * /var/www/aicouncil/scripts/backup_db.sh >> /var/log/aicouncil/backup.log 2>&1
```

### 9. 安全加固

#### 防火墙配置

```bash
# 使用ufw配置防火墙
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### 文件权限设置

```bash
# 设置项目目录权限
sudo chown -R www-data:www-data /var/www/aicouncil
sudo chmod 755 /var/www/aicouncil

# 环境变量文件权限（仅所有者可读）
sudo chmod 600 /var/www/aicouncil/.env

# 数据目录权限
sudo chmod 700 /var/www/aicouncil/data

# 工作空间权限
sudo chmod 755 /var/www/aicouncil/workspaces
```

#### Fail2ban配置（可选）

防止暴力破解攻击：

```bash
sudo apt install fail2ban
```

创建配置 `/etc/fail2ban/jail.d/aicouncil.conf`：

```ini
[aicouncil-auth]
enabled = true
port = http,https
filter = aicouncil-auth
logpath = /var/log/aicouncil/app.log
maxretry = 5
bantime = 3600
findtime = 600
```

创建过滤器 `/etc/fail2ban/filter.d/aicouncil-auth.conf`：

```ini
[Definition]
failregex = ^.*Failed login attempt for user.*from <HOST>$
ignoreregex =
```

重启fail2ban：
```bash
sudo systemctl restart fail2ban
```

### 10. 监控和告警（可选）

#### 应用健康检查

在应用中添加健康检查端点（已在`app.py`中实现）：

```python
@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200
```

#### 使用systemd监控

检查服务状态：
```bash
# 实时查看日志
journalctl -u aicouncil -f

# 查看最近100行日志
journalctl -u aicouncil -n 100

# 查看错误日志
journalctl -u aicouncil -p err
```

#### 磁盘空间监控

添加到crontab：
```bash
# 每天检查磁盘空间
0 9 * * * df -h | grep -E '(9[0-9]|100)%' && echo "Warning: Disk space running low" | mail -s "AICouncil Disk Alert" admin@example.com
```

## ✅ 部署验证清单

完成部署后，逐项检查：

### 配置验证
- [ ] SECRET_KEY已设置为随机值（≥32字节）
- [ ] FLASK_ENV=production
- [ ] SESSION_COOKIE_SECURE=true
- [ ] 数据库连接正常
- [ ] 配置验证脚本通过（`python scripts/validate_env.py`）

### 数据库验证
- [ ] 数据库迁移已应用（`flask db upgrade`）
- [ ] 管理员账户已创建（`flask create-admin`）
- [ ] 数据库备份任务已配置

### 服务验证
- [ ] Gunicorn服务运行正常（`systemctl status aicouncil`）
- [ ] Nginx配置正确（`sudo nginx -t`）
- [ ] SSL证书有效（`curl -I https://your-domain.com`）
- [ ] 反向代理工作正常

### 安全验证
- [ ] 防火墙规则已设置
- [ ] 文件权限正确设置
- [ ] 日志轮转已配置
- [ ] HTTP自动重定向到HTTPS
- [ ] HSTS头已启用

### 功能验证
- [ ] 登录页面可访问
- [ ] 管理员账户可登录
- [ ] MFA设置功能正常
- [ ] PDF导出功能正常（需Playwright）
- [ ] 议事功能正常

## 🔧 故障排查

### 常见问题

#### 1. SECRET_KEY警告
```
⚠️ SECRET_KEY未设置或使用默认值
```
**解决方案**：
- 运行 `flask generate-secret-key` 生成新密钥
- 更新 `.env` 文件中的 `SECRET_KEY`
- 确保 `.env` 权限为 600

#### 2. 数据库连接失败
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**解决方案**：
- 检查 `DATABASE_URL` 格式
- 确认数据库服务运行：`sudo systemctl status postgresql`
- 验证用户名和密码
- 检查防火墙规则

#### 3. Session失效
```
用户登录后立即被登出
```
**解决方案**：
- 确认 `SESSION_COOKIE_SECURE=true` 且使用HTTPS
- 检查 `PERMANENT_SESSION_LIFETIME` 设置
- 验证session表已创建：`flask db upgrade`

#### 4. MFA二维码不显示
```
/api/auth/mfa/setup 返回500错误
```
**解决方案**：
```bash
pip install pyotp qrcode[pil]
```

#### 5. Gunicorn启动失败
```
systemctl status aicouncil 显示failed
```
**解决方案**：
- 查看详细错误：`journalctl -u aicouncil -n 50`
- 检查Python路径和虚拟环境
- 验证工作目录权限
- 确认依赖已安装

### 查看日志

```bash
# 应用日志
tail -f /var/log/aicouncil/app.log

# Gunicorn错误日志
tail -f /var/log/aicouncil/error.log

# systemd日志
journalctl -u aicouncil -f

# Nginx错误日志
tail -f /var/log/nginx/error.log

# Nginx访问日志
tail -f /var/log/nginx/access.log
```

## 🔄 更新和回滚

### 更新应用

```bash
# 停止服务
sudo systemctl stop aicouncil

# 拉取最新代码
cd /var/www/aicouncil
git pull origin main

# 更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 运行数据库迁移
flask db upgrade

# 重启服务
sudo systemctl start aicouncil
```

### 回滚操作

如果更新出现问题：

```bash
# 停止服务
sudo systemctl stop aicouncil

# 回滚代码
git checkout <previous-commit-hash>

# 回滚数据库
flask db downgrade

# 或恢复数据库备份
gunzip < /var/backups/aicouncil/aicouncil_YYYYMMDD_HHMMSS.sql.gz | psql -U aicouncil_user aicouncil

# 重启服务
sudo systemctl start aicouncil
```

## 📊 性能优化建议

### 1. 数据库优化
- 使用连接池：`SQLAlchemy pool_size=20`
- 创建索引：`CREATE INDEX idx_username ON users(username);`
- 定期VACUUM（PostgreSQL）

### 2. Gunicorn优化
- Worker数量：`CPU核心数 * 2 + 1`
- 使用异步worker：`--worker-class gevent`
- 增加超时时间：`--timeout 300`

### 3. Nginx优化
- 启用gzip压缩
- 配置静态文件缓存
- 使用HTTP/2

### 4. Redis Session存储（可选）
```bash
pip install redis flask-session[redis]
```

更新`.env`：
```ini
SESSION_TYPE=redis
SESSION_REDIS=redis://localhost:6379/0
```

## 📞 技术支持

如遇到部署问题，请：
1. 查看日志文件
2. 运行配置验证脚本
3. 查阅常见问题部分
4. 提交Issue并附上详细日志
