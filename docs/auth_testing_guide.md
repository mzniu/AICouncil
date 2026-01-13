# 🧪 认证系统测试指南

## ✅ 初始化完成

数据库已成功初始化，测试用户已创建！

---

## 🔐 测试账号

| 项目 | 值 |
|------|-----|
| 用户名 | `testuser` |
| 密码 | `Test123!` |
| 邮箱 | `test@example.com` |

---

## 🚀 测试步骤

### 1. 启动应用

```bash
python src/web/app.py
```

### 2. 测试登录流程

#### Step 1: 访问首页（应自动跳转）
- 打开浏览器访问：`http://127.0.0.1:5000/`
- **预期结果**：自动跳转到 `/login` 登录页面

#### Step 2: 测试登录
- 输入用户名：`testuser`
- 输入密码：`Test123!`
- 点击"登录"
- **预期结果**：成功登录，跳转到首页 `/`

#### Step 3: 验证会话持久化
- 关闭浏览器标签页
- 重新打开 `http://127.0.0.1:5000/`
- **预期结果**：如果勾选了"记住我"，应直接进入首页；否则需要重新登录

#### Step 4: 测试登出
- 访问 `/api/auth/logout` (POST请求) 或前端实现登出按钮
- **预期结果**：会话清除，再次访问首页时需要重新登录

---

### 3. 测试注册流程（可选）

#### 启用公开注册
编辑 `.env` 文件：
```ini
ALLOW_PUBLIC_REGISTRATION=true
```

重启应用后：

1. 访问 `http://127.0.0.1:5000/register`
2. 填写注册信息：
   - 用户名：`newuser`
   - 密码：`NewPass123!`（必须符合密码策略）
   - 邮箱：`newuser@example.com`
3. 点击"注册"
4. **预期结果**：注册成功，自动跳转到登录页面

#### 测试密码策略
尝试使用弱密码注册（如 `123456`）：
- **预期结果**：显示错误提示，列出不符合的密码要求

---

### 4. 测试 MFA（多因素认证）

#### Step 1: 启用 MFA
1. 登录后访问 `/mfa-setup`
2. 使用手机上的 Authenticator 应用（Google Authenticator 或 Microsoft Authenticator）扫描 QR 码
3. 输入应用生成的 6 位验证码
4. **预期结果**：显示 10 个备份码，保存到安全位置

#### Step 2: 使用 MFA 登录
1. 登出账户
2. 重新登录（用户名 + 密码）
3. **预期结果**：跳转到 `/mfa-verify` 页面要求输入验证码
4. 输入 Authenticator 应用的 6 位验证码
5. **预期结果**：验证成功，进入首页

#### Step 3: 使用备份码登录
1. 在 MFA 验证页面点击"使用备份码"
2. 输入之前保存的 8 位备份码之一
3. **预期结果**：验证成功，该备份码被标记为已使用

---

### 5. 测试账户锁定

连续输入错误密码 5 次：
- **预期结果**：账户被锁定 5 分钟
- 错误消息：`"账户已锁定，请在 X 分钟后重试"`

---

### 6. 测试登录历史

查询 `LoginHistory` 表：
```python
from src.models import LoginHistory, db
from src.web.app import app

with app.app_context():
    history = LoginHistory.query.order_by(LoginHistory.timestamp.desc()).limit(10).all()
    for record in history:
        print(f"{record.timestamp} | {record.action} | Success: {record.success} | IP: {record.ip}")
```

**预期结果**：显示最近 10 条登录记录

---

## 🧪 运行自动化测试

```bash
# 运行所有认证测试
python -m pytest tests/test_auth_endpoints.py tests/test_mfa_security.py -v

# 运行单个测试
python -m pytest tests/test_auth_endpoints.py::TestLogin::test_login_success -v

# 查看覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

**预期结果**：41 passed, 1 skipped

---

## 🔍 常见问题排查

### 问题 1: 登录后立即跳转回登录页

**原因**：SECRET_KEY 未正确配置

**解决方法**：
```bash
# 生成新的 SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 更新 .env 文件
SECRET_KEY=your-generated-key-here
```

### 问题 2: 数据库表不存在

**解决方法**：
```bash
# 重新初始化数据库
python init_auth_db.py
```

### 问题 3: MFA 验证码总是错误

**原因**：手机时间与服务器时间不同步

**解决方法**：
- 确保手机时间自动同步
- 检查服务器时间：`python -c "import datetime; print(datetime.datetime.utcnow())"`

### 问题 4: 会话频繁过期

**原因**：SESSION_TYPE 配置问题

**解决方法**（在 `.env` 中）：
```ini
SESSION_TYPE=sqlalchemy  # 使用数据库存储会话
PERMANENT_SESSION_LIFETIME=2592000  # 30天
```

---

## 📊 测试检查清单

- [ ] ✅ 首页自动跳转到登录页
- [ ] ✅ 成功登录并进入首页
- [ ] ✅ 密码错误时显示错误提示
- [ ] ✅ 连续失败 5 次触发账户锁定
- [ ] ✅ "记住我"功能正常工作
- [ ] ✅ 登出后需要重新登录
- [ ] ✅ 注册功能正常（如已启用）
- [ ] ✅ 弱密码被拒绝
- [ ] ✅ MFA 设置成功生成 QR 码
- [ ] ✅ MFA 验证码可以正常验证
- [ ] ✅ 备份码可以使用（仅一次）
- [ ] ✅ 登录历史正确记录
- [ ] ✅ 所有 API 端点返回正确状态码

---

## 🎯 下一步

所有测试通过后，您可以：

1. **前端集成**：在 `index.html` 添加登出按钮
2. **权限控制**：为不同用户添加角色和权限
3. **邮箱验证**：实现注册邮箱验证功能
4. **密码重置**：实现忘记密码功能
5. **OAuth 登录**：集成 Google/GitHub 第三方登录

---

**祝测试顺利！** 🎉
