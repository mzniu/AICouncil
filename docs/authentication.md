# 🔐 AICouncil 认证系统文档

本文档详细介绍 AICouncil 的用户认证与安全系统，包括登录、注册、多因素认证（MFA）、会话管理等功能。

---

## 📋 目录

- [系统概述](#系统概述)
- [功能特性](#功能特性)
- [登录流程](#登录流程)
- [MFA 设置指南](#mfa-设置指南)
- [API 端点文档](#api-端点文档)
- [安全特性](#安全特性)
- [配置说明](#配置说明)
- [故障排查](#故障排查)

---

## 系统概述

AICouncil 认证系统基于 **Flask-Login** 和 **TOTP（基于时间的一次性密码）** 实现，提供企业级的安全保障。

### 技术栈

- **后端框架**: Flask + Flask-Login
- **数据库**: SQLAlchemy (支持 SQLite/PostgreSQL/MySQL)
- **密码加密**: Werkzeug + bcrypt
- **MFA 实现**: pyotp (TOTP RFC 6238)
- **QR 码生成**: qrcode + Pillow
- **会话管理**: Flask-Session (支持文件/Redis/数据库存储)

### 安全原则

1. **密码不可逆加密**：使用 bcrypt 算法，自动加盐
2. **会话版本控制**：登出时递增版本，旧会话自动失效
3. **账户锁定机制**：连续失败 5 次锁定 5 分钟（可配置）
4. **MFA 强制启用**：高权限用户可要求启用双因素认证
5. **备份码单次使用**：每个备份码仅能使用一次
6. **审计日志**：完整记录登录历史（成功/失败/IP/User-Agent）

---

## 功能特性

### ✅ 已实现

- ✅ **用户注册**：支持公开注册（可配置禁用）
- ✅ **密码策略**：可配置长度、复杂度要求
- ✅ **登录认证**：用户名/密码验证
- ✅ **MFA (TOTP)**：基于 Google Authenticator 等应用
- ✅ **备份码**：生成 10 个一次性备份码
- ✅ **会话管理**：支持"记住我"功能（30 天）
- ✅ **账户锁定**：防暴力破解
- ✅ **登录历史**：记录所有登录行为
- ✅ **登出所有设备**：通过会话版本控制实现

### ⏳ 待实现

- ⏳ **MFA 超时检查**：验证码输入超时自动失效
- ⏳ **邮箱验证**：注册时发送验证邮件
- ⏳ **密码重置**：通过邮箱重置密码
- ⏳ **OAuth 登录**：支持 Google/GitHub 第三方登录

---

## 登录流程

### 完整流程图

```mermaid
flowchart TD
    A[访问登录页] --> B{已登录?}
    B -->|是| C[跳转首页]
    B -->|否| D[输入用户名密码]
    D --> E{验证密码}
    E -->|失败| F{失败次数 >= 5?}
    F -->|是| G[锁定账户 5 分钟]
    F -->|否| H[显示错误提示]
    H --> D
    G --> D
    E -->|成功| I{启用了 MFA?}
    I -->|否| J[登录成功 → 首页]
    I -->|是| K[跳转 MFA 验证页]
    K --> L[输入 6 位 OTP 或备份码]
    L --> M{验证成功?}
    M -->|失败| N[显示错误]
    N --> L
    M -->|成功| J
```

### 第一步：基础认证

1. 访问 `/login` 页面
2. 输入用户名和密码
3. 可选：勾选"记住我"（30 天免登录）
4. 点击"登录"

**后端验证逻辑**：
```python
POST /api/auth/login
{
    "username": "your_username",
    "password": "your_password",
    "remember_me": true
}

# 成功响应（未启用 MFA）
{
    "message": "登录成功",
    "requires_mfa": false
}

# 成功响应（需要 MFA）
{
    "message": "请输入验证码",
    "requires_mfa": true
}
```

### 第二步：MFA 验证（如适用）

如果用户启用了 MFA，登录后会跳转到 `/mfa-verify` 页面：

1. 打开 Google Authenticator / Microsoft Authenticator 等应用
2. 输入 6 位动态验证码
3. 或者使用 8 位备份码（仅一次）

**验证码有效期**：30 秒（标准 TOTP 时间窗口）

---

## MFA 设置指南

### 启用 MFA（三步流程）

#### Step 1: 生成密钥

访问 `/mfa-setup` 或调用 API：

```bash
POST /api/auth/mfa/setup
Headers: Cookie: session=...

# 响应
{
    "qr_code": "data:image/png;base64,iVBORw0KG...",  # QR 码图片
    "secret": "JBSWY3DPEHPK3PXP",  # 手动输入用密钥
    "issuer": "AICouncil"
}
```

#### Step 2: 扫码并验证

1. 使用 Authenticator 应用扫描 QR 码
2. 或手动输入密钥（Secret）
3. 输入应用生成的 6 位验证码进行验证

```bash
POST /api/auth/mfa/verify
{
    "otp_code": "123456"
}

# 成功响应
{
    "message": "MFA 已启用",
    "backup_codes": [
        "12345678",
        "87654321",
        ...  # 共 10 个
    ]
}
```

#### Step 3: 保存备份码

⚠️ **重要**：将 10 个备份码保存到安全位置（密码管理器/纸质文档）

- 每个备份码仅能使用一次
- 丢失设备时可用备份码登录
- 备份码用完后需重新设置 MFA

### 禁用 MFA

需要提供当前密码进行确认：

```bash
POST /api/auth/mfa/disable
{
    "password": "current_password"
}

# 成功响应
{
    "message": "MFA 已禁用"
}
```

---

## API 端点文档

### 1. 注册 `/api/auth/register`

**方法**: `POST`  
**认证**: 不需要  
**限制**: 可通过环境变量禁用公开注册

**请求体**:
```json
{
    "username": "newuser",
    "password": "SecurePass123!",
    "email": "user@example.com"
}
```

**密码要求**（默认）:
- 最少 8 位
- 至少 1 个大写字母
- 至少 1 个小写字母
- 至少 1 个数字
- 至少 1 个特殊字符 (`!@#$%^&*(),.?":{}|<>`)

**响应**:
```json
// 201 Created
{
    "message": "注册成功",
    "user_id": 123
}

// 400 Bad Request - 密码不符合要求
{
    "error": {
        "length": "密码长度至少8位",
        "uppercase": "密码必须包含大写字母",
        "special": "密码必须包含特殊字符"
    }
}

// 403 Forbidden - 注册被禁用
{
    "error": "registration_disabled",
    "message": "公开注册已禁用，请联系管理员"
}
```

---

### 2. 登录 `/api/auth/login`

**方法**: `POST`  
**认证**: 不需要

**请求体**:
```json
{
    "username": "testuser",
    "password": "SecurePass123!",
    "remember_me": false
}
```

**响应**:
```json
// 200 OK - 无需 MFA
{
    "message": "登录成功",
    "requires_mfa": false
}

// 200 OK - 需要 MFA
{
    "message": "请输入验证码",
    "requires_mfa": true
}

// 401 Unauthorized - 密码错误
{
    "error": "用户名或密码错误"
}

// 403 Forbidden - 账户锁定
{
    "error": "账户已锁定",
    "message": "连续登录失败 5 次，账户已锁定 5 分钟"
}
```

---

### 3. MFA 设置 `/api/auth/mfa/setup`

**方法**: `POST`  
**认证**: 需要已登录

**请求体**: 无

**响应**:
```json
// 200 OK
{
    "qr_code": "data:image/png;base64,iVBORw0KG...",
    "secret": "JBSWY3DPEHPK3PXP",
    "issuer": "AICouncil"
}

// 401 Unauthorized - 未登录
{
    "error": "未登录"
}
```

**说明**:
- 即使已启用 MFA，也可重新调用此接口生成新密钥
- 旧密钥会被新密钥覆盖
- 旧备份码失效，需重新验证后生成新备份码

---

### 4. MFA 验证 `/api/auth/mfa/verify`

**方法**: `POST`  
**认证**: 需要处于 MFA pending 状态

**请求体**:
```json
{
    "otp_code": "123456"  // 6 位 OTP 或 8 位备份码
}
```

**响应**:
```json
// 200 OK - 首次验证（返回备份码）
{
    "message": "MFA 已启用",
    "backup_codes": [
        "12345678",
        "87654321",
        ...
    ]
}

// 200 OK - 日常登录验证
{
    "message": "验证成功"
}

// 401 Unauthorized - 验证码错误
{
    "error": "验证码错误"
}

// 400 Bad Request - 备份码已用完
{
    "error": "所有备份码已使用完毕，请重新设置 MFA"
}
```

---

### 5. MFA 禁用 `/api/auth/mfa/disable`

**方法**: `POST`  
**认证**: 需要已登录

**请求体**:
```json
{
    "password": "SecurePass123!"
}
```

**响应**:
```json
// 200 OK
{
    "message": "MFA 已禁用"
}

// 401 Unauthorized - 密码错误
{
    "error": "密码错误"
}
```

---

### 6. 登出 `/api/auth/logout`

**方法**: `POST`  
**认证**: 需要已登录

**请求体**: 无

**响应**:
```json
// 200 OK
{
    "message": "登出成功"
}
```

**副作用**:
- 递增用户的 `session_version`
- 所有旧会话（其他设备）自动失效
- 实现"登出所有设备"功能

---

### 7. 状态查询 `/api/auth/status`

**方法**: `GET`  
**认证**: 不需要

**响应**:
```json
// 已登录
{
    "authenticated": true,
    "username": "testuser",
    "user_id": 123,
    "mfa_enabled": true
}

// 未登录
{
    "authenticated": false
}
```

---

## 安全特性

### 1. 密码加密

使用 **Werkzeug** 的 `generate_password_hash()` 和 `check_password_hash()`：

```python
# 加密（自动加盐）
hashed = generate_password_hash(password, method='pbkdf2:sha256')

# 验证
is_valid = check_password_hash(hashed, password)
```

**算法**: PBKDF2-HMAC-SHA256  
**迭代次数**: 260,000+（Werkzeug 默认）

### 2. 会话管理

#### 会话版本控制

每个用户有一个 `session_version` 字段（整数）：

```python
# 登出时递增版本
user.session_version += 1
db.session.commit()

# 每次请求验证版本
@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if session.get('session_version') != user.session_version:
        return None  # 会话失效
    return user
```

**效果**:
- 登出后，其他设备的旧会话立即失效
- 修改密码后可强制登出所有设备

#### 会话配置

```python
# .env 配置
SESSION_TYPE=sqlalchemy              # 存储类型
PERMANENT_SESSION_LIFETIME=2592000   # 30 天（秒）
SESSION_COOKIE_HTTPONLY=true         # 防 XSS
SESSION_COOKIE_SECURE=true           # 仅 HTTPS
SESSION_COOKIE_SAMESITE=Lax          # CSRF 防护
```

### 3. 账户锁定

连续登录失败达到阈值后锁定账户：

```python
# 配置
ACCOUNT_LOCKOUT_THRESHOLD=5      # 失败 5 次锁定
ACCOUNT_LOCKOUT_DURATION=300     # 锁定 5 分钟

# 实现逻辑
if user.login_attempts >= threshold:
    lockout_until = user.last_failed_login + timedelta(seconds=duration)
    if now < lockout_until:
        return {"error": "账户已锁定"}, 403
```

**重置条件**:
- 成功登录后重置失败计数
- 锁定时间过期后可重试

### 4. SQL 注入防护

使用 SQLAlchemy ORM，所有查询自动参数化：

```python
# ✅ 安全（自动转义）
User.query.filter_by(username=username).first()

# ❌ 危险（避免使用）
db.session.execute(f"SELECT * FROM users WHERE username='{username}'")
```

### 5. XSS 防护

- **存储**: 原样保存用户输入（不转义）
- **输出**: Jinja2 自动转义 HTML

```html
<!-- 自动转义 -->
<p>用户名：{{ user.username }}</p>

<!-- 如需原样输出（危险） -->
<p>{{ content | safe }}</p>
```

### 6. CSRF 防护

Flask-WTF 集成 CSRF 保护：

```python
# API 端点禁用 CSRF（使用 session 验证）
app.config['WTF_CSRF_ENABLED'] = False

# 或在表单中添加 CSRF token
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

### 7. 审计日志

`LoginHistory` 表记录所有登录行为：

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | Integer | 用户 ID |
| `action` | String | 操作类型（login/register/mfa_verify） |
| `success` | Boolean | 是否成功 |
| `ip` | String | 来源 IP |
| `user_agent` | String | 浏览器信息 |
| `timestamp` | DateTime | 时间戳 |

---

## 配置说明

### 环境变量清单

在 `.env` 文件中配置以下参数：

#### 数据库配置
```ini
DATABASE_URL=sqlite:///aicouncil.db
# 或 PostgreSQL: postgresql://user:pass@localhost/aicouncil
```

#### 会话配置
```ini
SECRET_KEY=your-secret-key-min-32-bytes
SESSION_TYPE=sqlalchemy
PERMANENT_SESSION_LIFETIME=2592000
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=Lax
```

#### 注册控制
```ini
ALLOW_PUBLIC_REGISTRATION=true
```

#### 密码策略
```ini
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
```

#### 账户锁定
```ini
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_DURATION=300
```

#### MFA 配置
```ini
MFA_TIMEOUT=600  # MFA 验证超时（秒）
```

### 生成安全密钥

使用 Python 生成 SECRET_KEY：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

或使用 Flask CLI：

```bash
flask generate-secret-key
```

---

## 故障排查

### 1. 无法登录：密码正确但提示错误

**可能原因**:
- 账户锁定（连续失败 5 次）
- 数据库密码哈希损坏

**解决方法**:
```python
# 检查锁定状态
from src.models import User
user = User.query.filter_by(username='testuser').first()
print(f"失败次数: {user.login_attempts}")
print(f"最后失败时间: {user.last_failed_login}")

# 重置失败次数
user.login_attempts = 0
db.session.commit()
```

### 2. MFA 验证码总是错误

**可能原因**:
- 设备时间不同步（TOTP 依赖系统时间）
- 使用了旧的 secret（重新设置后需重新扫码）

**解决方法**:
1. 确保手机和服务器时间同步（误差 < 30 秒）
2. 重新访问 `/mfa-setup` 生成新 QR 码
3. 使用备份码登录，然后禁用并重新启用 MFA

### 3. 会话频繁过期

**可能原因**:
- `PERMANENT_SESSION_LIFETIME` 设置过短
- 服务器重启导致会话丢失（如使用文件存储）

**解决方法**:
```ini
# 延长会话时间（30 天）
PERMANENT_SESSION_LIFETIME=2592000

# 使用数据库存储会话（推荐）
SESSION_TYPE=sqlalchemy
```

### 4. 备份码用完后无法登录

**解决方案**:
1. 联系管理员直接禁用 MFA：
   ```python
   from src.models import db, User
   user = User.query.filter_by(username='username').first()
   user.mfa_enabled = False
   user.mfa_secret = None
   user.mfa_backup_codes = None
   db.session.commit()
   ```

2. 或通过邮箱重置（需实现邮箱验证功能）

### 5. 注册时提示"公开注册已禁用"

**原因**: 环境变量 `ALLOW_PUBLIC_REGISTRATION=false`

**解决方法**:
- 修改 `.env` 文件：`ALLOW_PUBLIC_REGISTRATION=true`
- 或联系管理员手动创建账户

### 6. 生产环境 SESSION_COOKIE_SECURE 警告

**原因**: 在非 HTTPS 环境启用了 `SESSION_COOKIE_SECURE=true`

**解决方法**:
- 开发环境：设置为 `false`
- 生产环境：配置 SSL 证书（推荐 Let's Encrypt）

---

## 安全检查清单

部署前请确认：

- [ ] `SECRET_KEY` 已设置且长度 ≥ 32 字节
- [ ] 生产环境使用 PostgreSQL/MySQL（避免 SQLite）
- [ ] `SESSION_COOKIE_SECURE=true`（HTTPS 环境）
- [ ] `SESSION_COOKIE_HTTPONLY=true`（防 XSS）
- [ ] 数据库备份策略已配置
- [ ] 日志记录已启用（`LOG_LEVEL=INFO`）
- [ ] 防火墙规则已配置（仅开放必要端口）
- [ ] 定期更新依赖（`pip list --outdated`）

---

## 参考资料

- [Flask-Login 官方文档](https://flask-login.readthedocs.io/)
- [pyotp 库文档](https://pyauth.github.io/pyotp/)
- [TOTP RFC 6238](https://tools.ietf.org/html/rfc6238)
- [OWASP 认证备忘单](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

**如有问题，请提交 Issue 或联系维护者。**
