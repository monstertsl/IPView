# IPVIEW - IP 地址监控与管理系统

基于 FastAPI + Vue 3 + PostgreSQL + Redis + Celery 的企业级 IP 地址监控与管理系统。

## 功能特性

- IP 可视化监控（20 列网格化展示）
- IP / MAC / 网段快速定位搜索
- SNMP 自动扫描核心交换机 ARP 表
- 轻量历史 MAC 追踪（Tooltip 展示）
- 完整登录 + 扫描日志审计
- 日志生命周期管理（自动 + 手动清理）
- RBAC 权限控制（admin / user）
- TOTP 多因素认证
- SNMP v1/v2c/v3 支持

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 前端 | Vue 3 + Naive UI + Pinia + Axios |
| 数据库 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| 异步任务 | Celery 5 |
| SNMP | pysnmp 6 |

## 快速启动

### 方式一：Docker Compose（推荐）

```bash
# 克隆项目后
docker-compose up -d

# 访问
# 前端: http://localhost:3000
# 后端: http://localhost:8000
# API 文档: http://localhost:8000/docs

# 默认管理员账号
# 用户名: admin
# 密码: admin123
```

### 方式二：本地开发

**后端**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置 .env
cp .env.example .env

# 初始化数据库并启动
uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker（新终端）
celery -A celery_app worker --loglevel=info

# 启动 Celery Beat 调度器（新终端）
celery -A celery_app beat --loglevel=info
```

**前端**

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── core/          # 核心模块（config, db, auth, redis, security）
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # 业务服务（SNMP 扫描）
│   │   ├── tasks/         # Celery 任务
│   │   └── main.py        # FastAPI 入口
│   ├── celery_app.py      # Celery 配置
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # Axios 实例
│   │   ├── router/       # Vue Router
│   │   ├── stores/       # Pinia 状态管理
│   │   ├── types/        # TypeScript 类型
│   │   ├── views/        # 页面组件
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

## 数据库模型

| 表名 | 说明 |
|------|------|
| `users` | 用户（支持 TOTP 加密存储） |
| `switches` | 交换机（SNMP 配置加密） |
| `ip_subnets` | 网段（CIDR） |
| `ip_records` | IP 当前状态（INET 类型） |
| `ip_events` | IP 历史事件（MAC 变化追踪） |
| `scan_tasks` | 扫描任务 |
| `scan_logs` | 扫描日志 |
| `login_logs` | 登录日志 |
| `system_config` | 系统配置 |

## API 概览

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出 |
| POST | `/api/auth/register` | 注册（admin） |

### IP 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ip/subnets` | 网段列表 |
| POST | `/api/ip/subnets` | 添加网段 |
| GET | `/api/ip/subnets/{id}/ips` | 获取网段内所有 IP |
| GET | `/api/ip/search?q=` | 搜索 IP/MAC/网段 |
| GET | `/api/ip/ip/{ip}/tooltip` | 获取 IP 详情（含历史） |

### 用户管理（admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/users` | 用户列表 |
| POST | `/api/users` | 添加用户 |
| PATCH | `/api/users/{id}` | 更新用户 |
| DELETE | `/api/users/{id}` | 删除用户 |
| POST | `/api/users/{id}/totp/enable` | 启用 TOTP |
| POST | `/api/users/{id}/totp/disable` | 禁用 TOTP |

### 交换机管理（admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/switches` | 交换机 CRUD |
| PATCH/DELETE | `/api/switches/{id}` | |

### 扫描管理（admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scan/config` | 扫描配置 |
| PATCH | `/api/scan/config` | 更新配置 |
| POST | `/api/scan/tasks/now` | 立即扫描 |
| GET | `/api/scan/tasks` | 任务历史 |

### 日志查询（admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/logs/login` | 登录日志 |
| POST | `/api/logs/cleanup` | 清理日志 |

## 权限矩阵

| 模块 | admin | user |
|------|-------|------|
| IP 管理 | ✅ | ✅ |
| 用户管理 | ✅ | ❌ |
| 交换机管理 | ✅ | ❌ |
| 扫描管理 | ✅ | ❌ |
| 日志查询 | ✅ | ❌ |

## 安全说明

- 用户密码使用 bcrypt 加密
- TOTP 密钥和 SNMPv3 配置使用 Fernet（PBKDF2）加密存储
- 所有接口需 Bearer Token 认证
- 登录失败 5 次后自动禁用账号（可配置）
- SQL 使用 SQLAlchemy ORM 参数化查询，防注入
- 所有输入经过 Pydantic 严格校验
