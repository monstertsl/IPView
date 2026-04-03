# 📋 智能 IP 地址监控与管理系统（最终开发需求文档 v3）

---

# 1️⃣ 项目概述

开发一个基于 Web 的 **IP 地址监控与管理系统（IPView）**，通过 SNMP 协议从核心交换机获取 ARP 表，实现 IP 使用状态的可视化管理、自动扫描、轻量历史追踪及日志审计。

---

## 🎯 核心目标

* 可视化展示 IP 使用状态（网格化）
* 支持 IP / MAC / 网段快速定位
* 自动扫描网络设备获取 ARP 数据
* 提供轻量历史 MAC 追踪能力
* 提供完整日志审计（登录 + 扫描）
* 支持日志生命周期管理（自动 + 手动清理）
* 实现严格权限控制

---

# 2️⃣ 技术架构

---

## 后端

* FastAPI（Python）
* SQLAlchemy ORM

---

## 数据库

### PostgreSQL（主库）

* 存储：

  * 用户
  * 系统配置
  * 交换机
  * IP 当前状态
  * IP 历史事件
  * 扫描任务
  * 日志

* 使用类型：

  * `INET`（IP）
  * `CIDR`（网段）
  * `JSONB`（SNMP v3 配置）

---

### Redis（缓存）

用于：

```text
Session Token
TOTP 临时数据
IP 实时状态缓存
```

---

## 前端

* Vue 3
* Naive UI

---

## 异步任务

* Celery（推荐）
* Redis / RabbitMQ 作为 Broker

---

## SNMP

* pysnmp

---

# 3️⃣ 权限模型（RBAC）

---

## 👥 角色定义

| 角色    | 权限      |
| ----- | ------- |
| admin | 全部功能    |
| user  | 仅 IP 管理 |

---

## 🔐 模块权限

| 模块    | admin | user |
| ----- | ----- | ---- |
| IP 管理 | ✅     | ✅    |
| 用户管理  | ✅     | ❌    |
| 交换机管理 | ✅     | ❌    |
| 扫描管理  | ✅     | ❌    |
| 日志查询  | ✅     | ❌    |

---

# 4️⃣ 数据库设计

---

## 4.1 系统配置表（system_config）

```text
id
online_days（默认7）
offline_days（默认15）
cleanup_days（默认30）

login_fail_limit
inactive_days_limit

log_retention_days_login（默认90）
log_retention_days_scan（默认30）
```

---

## 4.2 用户表（users）

```text
id (UUID)
username（唯一）
password_hash
totp_secret（加密存储）

role（admin/user）
auth_mode（PASSWORD_ONLY / TOTP_ONLY / PASSWORD_AND_TOTP）

is_active
failed_login_attempts
last_login_at
```

---

## 4.3 交换机表（switches）

```text
id
ip (INET)
mac

snmp_version（v1/v2c/v3）
community
snmp_v3_config（JSONB，加密）

location
```

---

## 4.4 网段表（ip_subnets）

```text
id
cidr（CIDR）
description
created_at
```

---

## 4.5 IP 当前状态表（ip_records）

```text
id
ip_address（INET，唯一索引）
mac_address

last_seen
status（可选字段）

created_at
```

---

## 4.6 IP 历史事件表（ip_events）

```text
id
ip_address
mac_address

event_type：
  NEW
  MAC_CHANGED

seen_at
```

👉 仅记录变化（不记录交换机）

---

## 4.7 扫描任务表（scan_tasks）

```text
id
status（PENDING / RUNNING / SUCCESS / FAILED）

started_at
finished_at
duration

total_ips
updated_ips

error_message
triggered_by（SYSTEM / MANUAL）

created_at
```

---

## 4.8 扫描日志表（scan_logs）

```text
id
task_id

status（SUCCESS / FAILED）
message
duration

created_at
```

---

## 4.9 登录日志表（login_logs）

```text
id
username
success

ip_address
user_agent
message

created_at
```

---

# 5️⃣ 系统模块设计

---

# 🧭 5.1 左侧菜单栏

---

## 功能

* 支持折叠 / 展开
* 支持权限控制显示

---

## 菜单结构

```text
IP管理
用户管理（admin）
交换机管理（admin）
扫描管理（admin）
日志查询（admin）
```

---

# 🧩 5.2 IP 管理模块（核心）

---

## 页面结构

### 左侧

* 网段列表（CIDR）
* 支持点击切换

---

### 右侧

* IP 网格（20~25列）
* 支持虚拟滚动

### 搜索功能
支持：
IP 精确搜索（高亮）
网段搜索（自动定位）
MAC 搜索（定位 IP）

---

---

## 🎨 状态规则

| 状态      | 条件                             |
| ------- | ------------------------------ |
| ONLINE  | ≤ online_days                  |
| OFFLINE | > online_days 且 ≤ offline_days |
| UNUSED  | > cleanup_days                 |


---

# 🧾 Tooltip

---

## 内容

```text
IP地址：10.10.0.99

状态：正常使用（绿色标签）

当前MAC地址：AA:BB:CC:DD:EE:FF

上次扫描时间：2026-04-03 12:30:21

历史MAC：
- AA:BB:CC:DD:EE:FF（当前）
- 11:22:33:44:55:66
- 77:88:99:AA:BB:CC
```

---

## 规则

* 最多显示 3~5 条
* 按时间倒序
* 去重
* 当前 MAC 高亮

---

## 交互

| 操作    | 行为         |
| ----- | ---------- |
| hover | 显示 Tooltip |
| click | 无操作        |

---

---

# 👤 5.3 用户管理（admin）

---

## 功能

* 用户增删改查
* 角色管理
* 启用 / 禁用
* MFA 配置

---

## 安全策略

* 登录失败次数限制
* 长期未登录禁用
* 界面超时时间自定义

认证与安全
可选勾选认证方式（密码/TOTP），支持三种认证模式：用户名+密码、用户名+TOTP、用户名+密码+TOTP。
TOTP:
支持开启/关闭。
密钥可见性: 在绑定 TOTP 时，必须显示二维码 以及 明文密钥字符串 (以便用户手动复制)。
管理员可在用户管理中查看用户的 TOTP 密钥 (文本形式，用于手动输入到验证器)。

---

# 🌐 5.4 交换机管理（admin）

---

## 功能

* 添加 / 编辑 / 删除

---

## SNMP 配置

| 版本     | 配置            |
| ------ | ------------- |
| v1/v2c | community     |
| v3     | 用户名 + 认证 + 加密 |

---

---

# 🔄 5.5 扫描管理（admin）

---

## 配置

```text
扫描间隔
SNMP超时
SNMP重试

在线/离线/清理阈值
```

---

## 操作

* 立即扫描

---

## 扫描流程

```text
创建任务 → 扫描 → 更新IP → 写日志 → 完成
```

---

---

# 📜 5.6 日志查询（admin ONLY）

---

## 子模块

### 1️⃣ 登录日志

* 用户名
* 状态
* IP
* 时间

---

### 2️⃣ 扫描日志

* 任务列表
* 扫描结果

---

---

## 🧹 日志管理

---

### 配置

```text
登录日志保留天数（默认90）
扫描日志保留天数（默认30）
```

---

### 自动清理

* 每日执行

---

### 手动清理

```http
POST /api/logs/cleanup
```

```json
{
  "type": "login | scan",
  "days": 30
}
```

---

---

# 6️⃣ 核心业务逻辑

---

## SNMP 扫描

* 从核心交换机获取 ARP 表
* 更新 ip_records

---

## IP 更新逻辑

```text
扫描到：
→ 更新 last_seen + MAC

MAC变化：
→ 写入 ip_events
```

---

## 状态计算（推荐实时）

```text
基于 last_seen 计算
```

---

## 登录逻辑

* 成功 → 重置失败次数
* 失败 → +1
* 超限 → 禁用

---

## 日志清理

* 自动 + 手动

---

# 7️⃣ 性能要求

---

## 必须满足

* 网段数据一次性加载
* Tooltip 不触发请求
* 批量 upsert 数据库

---

## Redis 使用

```text
缓存IP状态
```

---

## 前端

* 虚拟滚动
* Tooltip 本地数据渲染

---

# 8️⃣ 安全要求

---

* TOTP secret 加密存储
* SNMP v3 配置加密
* 登录日志记录
* 权限校验（RBAC）

---

# 9️⃣ 可扩展性

---

未来支持：

* VLAN
* 端口数据
* 安全分析（ARP 欺骗）
* 设备识别

---

---

# 🔐 系统安全规范与防护要求

为保障 IP 地址管理系统的安全性，必须在设计与开发过程中严格遵循以下安全规范，防止 SQL 注入、越权访问及敏感信息泄露等风险。

---

## 1️⃣ SQL 注入防护

系统必须杜绝一切形式的 SQL 注入风险：

* 严禁通过字符串拼接构造 SQL 语句
* 所有数据库操作必须使用 ORM 或参数化查询机制
* 所有用户输入（包括 IP、MAC、网段、搜索条件等）必须进行：

  * 类型校验
  * 格式校验
  * 长度限制

任何未经校验的数据不得直接参与数据库查询。

---

## 2️⃣ 权限控制（防止越权）

系统必须实现严格的基于角色的访问控制（RBAC）：

* 所有接口必须进行身份认证与权限校验
* 权限控制必须在后端实现，前端仅作为辅助展示
* 不同角色（admin / user）必须严格隔离功能权限
* 用户不得访问或操作超出自身权限范围的数据或接口

必须防止以下行为：

* 普通用户访问管理员接口
* 用户操作非授权资源
* 通过篡改请求绕过权限控制

---

## 3️⃣ 认证与会话安全

* 用户密码必须加密存储，禁止明文保存
* 支持多因素认证（TOTP）时，密钥必须加密存储
* 登录会话必须具备过期机制
* 应防止会话劫持、重放攻击等风险

---

## 4️⃣ 敏感信息保护

以下信息必须严格保护，禁止明文存储或泄露：

* 用户密码
* TOTP 密钥
* SNMP v3 认证与加密信息
* 系统密钥与 Token

敏感数据必须进行加密存储，并避免出现在日志或接口响应中。

---

## 5️⃣ 输入校验与数据安全

系统必须对所有外部输入进行统一校验：

* 使用统一的数据校验机制（如模型校验）
* 禁止直接信任前端输入
* 防止恶意构造输入导致系统异常或安全问题

---

## 6️⃣ 日志与审计安全

系统必须具备完整的日志审计能力：

* 记录登录行为（成功与失败）
* 记录关键操作（如扫描、配置修改）
* 支持日志查询与生命周期管理

同时必须确保：

* 日志中不得包含敏感信息
* 日志数据防篡改、防滥用

---

## 7️⃣ 防暴力破解与接口滥用

* 登录接口必须限制失败次数，并支持账号锁定机制
* 应限制请求频率，防止暴力攻击或接口滥用
* 关键操作接口必须具备额外保护措施

---

## 8️⃣ 最小权限原则

* 所有用户仅应拥有完成其任务所需的最小权限
* 数据库账号不得使用高权限账户（如 superuser）
* 各模块访问权限必须严格隔离

---

## 9️⃣ 安全设计原则

系统整体需遵循以下安全原则：

* 默认拒绝（Default Deny）
* 最小暴露面（Minimize Attack Surface）
* 分层防御（Defense in Depth）
* 零信任输入（Never Trust Input）

---

## ✅ 安全基线要求

系统上线前必须确保：

* 无 SQL 注入风险
* 无越权访问漏洞
* 所有接口均经过认证与授权
* 所有输入均经过校验
* 敏感信息已加密存储
* 日志体系完整且安全

---



# ✅ 最终总结

该系统实现：

✔ IP 可视化监控
✔ 轻量历史追踪（MAC）
✔ 扫描任务管理
✔ 完整日志体系
✔ 日志生命周期管理
✔ 极简交互（Tooltip为核心）
✔ 企业级可扩展架构

---

生成全量前后端代码和配置文档