# IPView - IP 地址监控与管理系统

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Vue%203-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" />
</p>

[中文](./README.md) | [English](./README_EN.md)

基于 **FastAPI + Vue 3 + PostgreSQL + Redis + Celery** 的企业级 IP 地址监控与管理系统，通过 SNMP 协议自动采集核心交换机 ARP 表，实时掌握全网 IP 使用状态。

超轻量化部署，单机2GB内存、2GB磁盘的轻量级服务器即可从容承载 5000+ IP的实时监控需求，实测7台交换机，5000个IP结果，整体项目仅占用 ≈ 724MB存储空间（镜像：652.40 MB，数据卷：68.87 MB，容器层	2.74 MB），项目整体消耗内存 ≈ 1.52GB（Docker本身：277 MB，IPView：1.25GB）。

---

![demo.png](./demo.png)

## 功能特性

- **IP 可视化监控** — 15-22列动态网格化展示整个 /24 网段（256 个 IP），在线/离线/空闲一目了然
- **智能搜索** — 支持 IP、MAC 地址、网段 CIDR 精确/模糊搜索，搜索 IP 可查看历史 MAC 变化，搜索 MAC 可查看历史分配 IP
- **SNMP 自动扫描** — 定时采集核心交换机 ARP 表，支持 SNMPv1/v2c/v3，三态状态（SUCCESS/PARTIAL/FAILED）
- **网段自动发现** — 扫描时自动根据发现的 IP 创建 /24 网段，仅创建匹配入库网段的网段
- **入库网段过滤** — 可配置仅允许指定网段的 IP 入库，不匹配的自动清理
- **MAC 变更追踪** — Tooltip 悬浮 + 搜索结果均展示 IP 历史 MAC 变化记录（最多 5 条），当前使用绿色标注
- **完整审计日志** — 登录日志 + 扫描日志，支持自动/手动清理
- **RBAC 权限控制** — admin / user 两级角色
- **TOTP 多因素认证** — 支持 Google Authenticator 等 TOTP 应用
- **数据加密存储** — TOTP 密钥、SNMP 配置使用 Fernet 加密

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 前端 | Vue 3 + Naive UI + TypeScript + Axios |
| 数据库 | PostgreSQL 16（INET/CIDR 原生类型） |
| 缓存 | Redis 7 |
| 异步任务 | Celery 5 + Beat 定时调度 |
| SNMP | pysnmp 6（lextudio） |
| 部署 | Docker Compose |

## 快速启动

### Docker Compose（推荐）

```bash
git clone https://github.com/monstertsl/IPView.git
cd IPView
```

> **首次启动前必读**：`docker-compose.yml` 顶部 `x-backend-env` 锚点中的 `SECRET_KEY` 与 `ENCRYPT_KEY` 默认是占位值，请务必替换为强随机值，否则后端会因密钥校验失败拒绝启动（`Field required` 或 `min_length` 错误）。
>
> 各自生成一把 64 位十六进制密钥：
>
> ```bash
> openssl rand -hex 32   # 用作 SECRET_KEY
> openssl rand -hex 32   # 用作 ENCRYPT_KEY
> ```
>
> 把生成结果替换到 `docker-compose.yml` 中：
>
> ```yaml
> x-backend-env: &backend-env
>   SECRET_KEY: <粘贴第一条 openssl 输出>
>   ENCRYPT_KEY: <粘贴第二条 openssl 输出>
> ```
>
> - **`SECRET_KEY`**：JWT 签名密钥。可随时更换，更换后所有用户被强制重新登录，无数据损失。
> - **`ENCRYPT_KEY`**：对称加密密钥，用于 TOTP / SNMP community / SNMPv3 凭据等。**部署后变更必须执行迁移脚本**，详见下文 [`## ENCRYPT_KEY 变更`](#encrypt_key-变更)。

```bash
docker compose up -d
```

启动后访问：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |

默认管理员账号：`admin` / `admin123`

> **提示**：首次使用请在「交换机管理」添加交换机后执行扫描，系统会自动发现并创建网段。

### 本地开发

**后端**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 启动 API 服务
uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker（新终端）
celery -A celery_app worker --loglevel=info

# 启动 Celery Beat（新终端）
celery -A celery_app beat --loglevel=info
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
IPView/
├── backend/
│   ├── app/
│   │   ├── api/            # API 路由（ip, scan, switch, user, log）
│   │   ├── core/           # 核心模块（config, database, auth, redis, security）
│   │   ├── models/         # SQLAlchemy ORM 模型
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── services/       # 业务服务（SNMP 扫描器）
│   │   ├── tasks/          # Celery 异步任务（扫描、定时清理）
│   │   └── main.py         # FastAPI 应用入口
│   ├── celery_app.py       # Celery 配置
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios 实例与拦截器
│   │   ├── router/         # Vue Router 路由配置
│   │   ├── stores/         # Pinia 状态管理（auth, theme）
│   │   ├── types/          # TypeScript 类型定义
│   │   ├── utils/          # 工具函数（时间格式化等）
│   │   ├── views/          # 页面组件
│   │   ├── App.vue
│   │   └── main.ts
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 数据库模型

| 表名 | 说明 |
|------|------|
| `users` | 用户账号（密码 bcrypt 加密，TOTP 密钥 Fernet 加密） |
| `switches` | 交换机（SNMPv3 配置 Fernet 加密） |
| `ip_subnets` | IP 网段（CIDR，支持自动发现） |
| `ip_records` | IP 当前状态（PostgreSQL INET 原生类型） |
| `ip_events` | IP 历史事件（MAC 变更追踪） |
| `scan_subnets` | 入库网段过滤规则 |
| `scan_tasks` | 扫描任务记录（SUCCESS/PARTIAL/FAILED 三态） |
| `login_logs` | 用户登录日志 |
| `system_config` | 系统全局配置 |

## API 概览

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录（支持 TOTP） |
| POST | `/api/auth/logout` | 登出 |
| POST | `/api/auth/check-user` | 检查用户状态 |

### IP 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ip/subnets` | 网段列表 |
| POST | `/api/ip/subnets` | 添加网段（自动预填充 IP） |
| DELETE | `/api/ip/subnets/{id}` | 删除网段 |
| GET | `/api/ip/subnets/{id}/ips` | 获取网段完整 IP 列表（256 个） |
| GET | `/api/ip/search?q=` | 搜索 IP / MAC / 网段（含历史记录） |
| GET | `/api/ip/ip/{ip}/tooltip` | IP 详情与历史 MAC |

### 用户管理（admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/users` | 用户列表 |
| POST | `/api/users` | 创建用户 |
| PATCH | `/api/users/{id}` | 更新用户 |
| DELETE | `/api/users/{id}` | 删除用户 |
| POST | `/api/users/{id}/totp/enable` | 启用 TOTP |
| POST | `/api/users/{id}/totp/disable` | 禁用 TOTP |

### 交换机管理（admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/switches` | 交换机列表 |
| POST | `/api/switches` | 添加交换机 |
| PATCH | `/api/switches/{id}` | 更新交换机 |
| DELETE | `/api/switches/{id}` | 删除交换机 |
| POST | `/api/switches/test` | 测试 SNMP 连接 |

### 扫描管理（admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scan/config` | 获取扫描配置 |
| PATCH | `/api/scan/config` | 更新扫描配置 |
| POST | `/api/scan/tasks/now` | 立即执行扫描 |
| GET | `/api/scan/tasks` | 扫描任务历史（SUCCESS/PARTIAL/FAILED） |
| GET/POST/DELETE | `/api/scan/subnets` | 入库网段管理 |

### 日志查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/logs/login` | 登录日志（分页） |
| GET | `/api/scan/tasks` | 扫描日志（任务级汇总） |
| POST | `/api/logs/cleanup` | 手动清理日志 |

## 权限矩阵

| 模块 | admin | user |
|------|:-----:|:----:|
| IP 管理 | ✅ | ✅ |
| 用户管理 | ✅ | ❌ |
| 交换机管理 | ✅ | ❌ |
| 扫描管理 | ✅ | ❌ |
| 日志查询 | ✅ | ❌ |

## 安全说明

- 用户密码 bcrypt 加密存储
- TOTP 密钥、SNMP 配置使用 Fernet（PBKDF2）对称加密
- 所有 API 接口需 Bearer Token（JWT）认证
- 登录连续失败 5 次自动禁用账号
- SQL 查询使用 SQLAlchemy ORM 参数化，防注入
- 所有输入经 Pydantic v2 严格校验

## ENCRYPT_KEY 变更

`ENCRYPT_KEY` 是用于加密以下数据库字段的对称密钥：

- `users.totp_secret_encrypted`（TOTP 密钥）
- `switches.community_encrypted`（SNMPv1/v2c community）
- `switches.snmp_v3_config_encrypted`（SNMPv3 凭据）

> ⚠️ **直接修改 `ENCRYPT_KEY` 后果严重**：旧密文将无法解密，TOTP 用户无法登录、所有交换机扫描失败。**必须使用项目根目录下的 `rotate_encrypt_key.py` 脚本完成重加密迁移。**

### 1. 生成新 key

```bash
openssl rand -hex 32
```

### 2. 验证旧 key 是否仍然能解密所有数据（只读，不改库）

```bash
docker exec -i -e PYTHONPATH=/app -e OLD_ENCRYPT_KEY='<当前 ENCRYPT_KEY>' -e MODE=verify ipview-backend-1 python - < /root/IPView/rotate_encrypt_key.py
```

输出形如 `ok=N failed=0` 表示旧 key 完全正确，可继续。任何 `failed > 0` 都不要继续迁移。

### 3. 停掉 Celery，避免迁移过程中扫描读取 community

```bash
docker compose stop celery celery-beat
```

### 4. 执行迁移：用旧 key 解密、用新 key 重加密、写回

```bash
docker exec -i -e PYTHONPATH=/app -e OLD_ENCRYPT_KEY='<旧 key>' -e NEW_ENCRYPT_KEY='<新 key>' -e MODE=rotate ipview-backend-1 python - < /root/IPView/rotate_encrypt_key.py
```

期望看到所有目标表的 `rotated=N`、无 `failed`。脚本在单一事务内执行，中途任何失败都会自动回滚，不会留下半套数据。

### 5. 把新 key 写回 `docker-compose.yml`

编辑顶部 `x-backend-env` 锚点：

```yaml
x-backend-env: &backend-env
  ENCRYPT_KEY: <新 key>
```

### 6. 重启服务让新 key 生效

```bash
docker compose up -d backend celery celery-beat
docker compose restart frontend   # 重建后 backend IP 变化时需要刷新 nginx upstream 缓存
```

### 7. 用新 key 再做一次只读校验

```bash
docker exec -i -e PYTHONPATH=/app -e OLD_ENCRYPT_KEY='<新 key>' -e MODE=verify ipview-backend-1 python - < /root/IPView/rotate_encrypt_key.py
```

`failed=0` 即迁移闭环完成。

### 关于 `SECRET_KEY` 的更换

`SECRET_KEY` 仅用于 JWT 签名，**不参与数据库加密**，因此可随时更换：

```bash
sed -i "s|SECRET_KEY: .*|SECRET_KEY: $(openssl rand -hex 32)|" docker-compose.yml
docker compose up -d backend celery celery-beat
```

副作用：所有在线用户的旧 token 立刻失效，需要重新登录。

## 故障恢复

无法登录前端时，可通过命令行直接操作。以下命令中 `ipview-postgres-1` 和 `ipview-backend-1` 为默认容器名。

### 查看用户状态

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "SELECT username, role, is_active, (totp_secret_encrypted IS NOT NULL) AS totp_enabled, failed_login_attempts, auth_mode FROM users;"
```

```
 username | role  | is_active | totp_enabled | failed_login_attempts |   auth_mode
----------+-------+-----------+--------------+-----------------------+---------------
 admin    | admin | f         | t            |                     5 | PASSWORD_ONLY
```

### 重置用户密码

**第一步：生成密码哈希**（将 `newpassword` 替换为你要设置的密码）

```bash
docker exec -it ipview-backend-1 python -c \
  "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('newpassword'))"
```

输出示例：`$2b$12$LJ3m4ys4Rz...`

**第二步：更新数据库**（将 `$2b$12$...` 替换为上一步的输出）

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET password_hash='\$2b\$12\$LJ3m4ys4Rz...' WHERE username='admin';"
```

### 解锁被禁用的账号

登录连续失败 5 次后账号会被自动禁用，使用以下命令解锁：

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET failed_login_attempts=0, is_active=true WHERE username='admin';"
```

### 一键重置（密码 + 解锁 + 禁用 TOTP）

最常见的场景——忘记密码 + 账号被锁 + TOTP 丢失，一条命令全部搞定，密码重置为 `admin123`：

```bash
docker exec -it ipview-backend-1 python -c "
from passlib.context import CryptContext
import subprocess, sys
h = CryptContext(schemes=['bcrypt']).hash('admin123')
sql = f\"UPDATE users SET password_hash='{h}', failed_login_attempts=0, is_active=true, totp_secret_encrypted=null, auth_mode='PASSWORD_ONLY' WHERE username='admin';\"
subprocess.run(['psql', '-h', 'postgres', '-U', 'postgres', '-d', 'ipview', '-c', sql], env={**__import__('os').environ, 'PGPASSWORD': 'postgres'})
"
```

### 禁用 TOTP

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET totp_secret_encrypted=null, auth_mode='PASSWORD_ONLY' WHERE username='admin';"
```

### 切换认证模式为纯密码

如果用户被设为 TOTP-only 模式导致无法登录：

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET auth_mode='PASSWORD_ONLY', totp_secret_encrypted=null WHERE username='admin';"
```

### 创建新管理员

当所有管理员账号都无法恢复时，可直接创建一个新的：

```bash
docker exec -it ipview-backend-1 python -c "
from passlib.context import CryptContext
import subprocess, os
h = CryptContext(schemes=['bcrypt']).hash('admin123')
sql = f\"INSERT INTO users (id, username, password_hash, role, auth_mode, is_active, failed_login_attempts, created_at, updated_at) VALUES (gen_random_uuid(), 'newadmin', '{h}', 'admin', 'PASSWORD_ONLY', true, 0, now(), now()) ON CONFLICT (username) DO NOTHING;\"
subprocess.run(['psql', '-h', 'postgres', '-U', 'postgres', '-d', 'ipview', '-c', sql], env={**os.environ, 'PGPASSWORD': 'postgres'})
"
```

### 启用/禁用用户

手动启用被禁用的用户：

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET is_active=true WHERE username='admin';"
```

手动禁用用户：

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET is_active=false WHERE username='test';"
```

## License

MIT
