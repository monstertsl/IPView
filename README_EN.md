# IPView - IP Address Monitoring and Management System

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Vue%203-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" />
</p>

[中文](./README.md) | [English](./README_EN.md)

An enterprise-grade IP address monitoring and management system built with **FastAPI + Vue 3 + PostgreSQL + Redis + Celery**. It automatically collects ARP tables from core switches via SNMP to provide real-time visibility into IP usage across the network.

Ultra-lightweight deployment: a server with only 2 GB RAM and 2 GB disk comfortably handles 5000+ IPs of real-time monitoring. Measured on 7 switches with 5000 IPs, the whole project occupies about 724 MB on disk (images: 652.40 MB, volumes: 68.87 MB, container layers: 2.74 MB) and uses about 1.52 GB of memory at runtime (Docker itself: 277 MB; IPView: 1.25 GB).

---

![demo.png](./demo.png)

## Features

- **IP Visualization Monitoring** — Dynamically displays an entire /24 subnet (256 IPs) in a 15-22 column grid, making online/offline/unused states clear at a glance
- **Intelligent Search** — Supports exact and fuzzy search by IP, MAC address, and subnet CIDR. Searching by IP shows MAC change history, while searching by MAC shows historical IP assignments
- **Automatic SNMP Scanning** — Periodically collects ARP tables from core switches, supports SNMPv1/v2c/v3, and provides three task states: SUCCESS / PARTIAL / FAILED
- **Automatic Subnet Discovery** — Automatically creates /24 subnets based on discovered IPs during scanning, but only for matched subnets allowed into storage
- **Subnet Allowlist Filtering** — Supports configuration to allow only specific subnets to be stored; unmatched records are automatically cleaned up
- **MAC Change Tracking** — Both tooltip hover and search results display IP MAC change history (up to 5 records), with the current MAC highlighted in green
- **Comprehensive Audit Logs** — Login logs and scan logs, with support for both automatic and manual cleanup
- **RBAC Access Control** — Two roles: admin / user
- **TOTP-Based Multi-Factor Authentication** — Supports Google Authenticator and other TOTP apps
- **Encrypted Data Storage** — TOTP secrets and SNMP configuration are encrypted with Fernet

## Tech Stack

| Layer | Technology |
|------|------|
| Backend | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Frontend | Vue 3 + Naive UI + TypeScript + Axios |
| Database | PostgreSQL 16 (native INET/CIDR types) |
| Cache | Redis 7 |
| Async Tasks | Celery 5 + Beat scheduling |
| SNMP | pysnmp 6 (lextudio) |
| Deployment | Docker Compose |

## Quick Start

### Docker Compose (Recommended)

```bash
git clone https://github.com/monstertsl/IPView.git
cd IPView
docker compose up -d
```

After startup, visit:

| Service | URL |
|------|------|
| Frontend | http://localhost:3000 |

Default admin account: `admin` / `admin123`

> **Tip**: On first use, add a switch in **Switch Management** and then start a scan. The system will automatically discover and create subnets.

### Local Development

**Backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Start API service
uvicorn app.main:app --reload --port 8000

# Start Celery Worker (new terminal)
celery -A celery_app worker --loglevel=info

# Start Celery Beat (new terminal)
celery -A celery_app beat --loglevel=info
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
IPView/
├── backend/
│   ├── app/
│   │   ├── api/            # API routes (ip, scan, switch, user, log)
│   │   ├── core/           # Core modules (config, database, auth, redis, security)
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── services/       # Business services (SNMP scanner)
│   │   ├── tasks/          # Celery async tasks (scanning, scheduled cleanup)
│   │   └── main.py         # FastAPI application entry point
│   ├── celery_app.py       # Celery configuration
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios instance and interceptors
│   │   ├── router/         # Vue Router configuration
│   │   ├── stores/         # Pinia state management (auth, theme)
│   │   ├── types/          # TypeScript type definitions
│   │   ├── utils/          # Utility functions (time formatting, etc.)
│   │   ├── views/          # Page components
│   │   ├── App.vue
│   │   └── main.ts
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Database Models

| Table | Description |
|------|------|
| `users` | User accounts (passwords encrypted with bcrypt, TOTP secrets encrypted with Fernet) |
| `switches` | Switches (SNMPv3 configuration encrypted with Fernet) |
| `ip_subnets` | IP subnets (CIDR, supports automatic discovery) |
| `ip_records` | Current IP status (PostgreSQL native INET type) |
| `ip_events` | IP history events (MAC change tracking) |
| `scan_subnets` | Subnet allowlist rules |
| `scan_tasks` | Scan task records (SUCCESS / PARTIAL / FAILED) |
| `login_logs` | User login logs |
| `system_config` | Global system configuration |

## API Overview

### Authentication

| Method | Path | Description |
|------|------|------|
| POST | `/api/auth/login` | Login (supports TOTP) |
| POST | `/api/auth/logout` | Logout |
| POST | `/api/auth/check-user` | Check user status |

### IP Management

| Method | Path | Description |
|------|------|------|
| GET | `/api/ip/subnets` | List subnets |
| POST | `/api/ip/subnets` | Add subnet (automatically pre-populates IPs) |
| DELETE | `/api/ip/subnets/{id}` | Delete subnet |
| GET | `/api/ip/subnets/{id}/ips` | Get the full IP list of a subnet (256 IPs) |
| GET | `/api/ip/search?q=` | Search by IP / MAC / subnet (including history) |
| GET | `/api/ip/ip/{ip}/tooltip` | IP details and historical MACs |

### User Management (admin)

| Method | Path | Description |
|------|------|------|
| GET | `/api/users` | List users |
| POST | `/api/users` | Create user |
| PATCH | `/api/users/{id}` | Update user |
| DELETE | `/api/users/{id}` | Delete user |
| POST | `/api/users/{id}/totp/enable` | Enable TOTP |
| POST | `/api/users/{id}/totp/disable` | Disable TOTP |

### Switch Management (admin)

| Method | Path | Description |
|------|------|------|
| GET | `/api/switches` | List switches |
| POST | `/api/switches` | Add switch |
| PATCH | `/api/switches/{id}` | Update switch |
| DELETE | `/api/switches/{id}` | Delete switch |
| POST | `/api/switches/test` | Test SNMP connectivity |

### Scan Management (admin)

| Method | Path | Description |
|------|------|------|
| GET | `/api/scan/config` | Get scan configuration |
| PATCH | `/api/scan/config` | Update scan configuration |
| POST | `/api/scan/tasks/now` | Run scan immediately |
| GET | `/api/scan/tasks` | Scan task history (SUCCESS / PARTIAL / FAILED) |
| GET/POST/DELETE | `/api/scan/subnets` | Manage allowed subnets |

### Log Queries

| Method | Path | Description |
|------|------|------|
| GET | `/api/logs/login` | Login logs (paginated) |
| GET | `/api/scan/tasks` | Scan logs (task-level summary) |
| POST | `/api/logs/cleanup` | Clean up logs manually |

## Permission Matrix

| Module | admin | user |
|------|:-----:|:----:|
| IP Management | ✅ | ✅ |
| User Management | ✅ | ❌ |
| Switch Management | ✅ | ❌ |
| Scan Management | ✅ | ❌ |
| Log Queries | ✅ | ❌ |

## Security Notes

- User passwords are stored with bcrypt hashing
- TOTP secrets and SNMP configuration use Fernet (PBKDF2) symmetric encryption
- All API endpoints require Bearer Token (JWT) authentication
- Accounts are automatically disabled after 5 consecutive failed login attempts
- SQL queries use SQLAlchemy ORM parameterization to prevent injection
- All input is strictly validated with Pydantic v2

## Disaster Recovery

If you cannot log in to the frontend, you can operate directly from the command line. In the following commands, `ipview-postgres-1` and `ipview-backend-1` are the default container names.

### Check User Status

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "SELECT username, role, is_active, (totp_secret_encrypted IS NOT NULL) AS totp_enabled, failed_login_attempts, auth_mode FROM users;"
```

```
 username | role  | is_active | totp_enabled | failed_login_attempts |   auth_mode
----------+-------+-----------+--------------+-----------------------+---------------
 admin    | admin | f         | t            |                     5 | PASSWORD_ONLY
```

### Reset User Password

**Step 1: Generate a password hash** (replace `newpassword` with the password you want to set)

```bash
docker exec -it ipview-backend-1 python -c \
  "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('newpassword'))"
```

Example output: `$2b$12$LJ3m4ys4Rz...`

**Step 2: Update the database** (replace `$2b$12$...` with the output from the previous step)

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET password_hash='\$2b\$12\$LJ3m4ys4Rz...' WHERE username='admin';"
```

### Unlock a Disabled Account

After 5 consecutive failed login attempts, the account is automatically disabled. Use the following command to unlock it:

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET failed_login_attempts=0, is_active=true WHERE username='admin';"
```

### One-Command Reset (Password + Unlock + Disable TOTP)

This is the most common recovery scenario—forgotten password, locked account, and lost TOTP. The following command fixes all of them at once and resets the password to `admin123`:

```bash
docker exec -it ipview-backend-1 python -c "
from passlib.context import CryptContext
import subprocess, sys
h = CryptContext(schemes=['bcrypt']).hash('admin123')
sql = f\"UPDATE users SET password_hash='{h}', failed_login_attempts=0, is_active=true, totp_secret_encrypted=null, auth_mode='PASSWORD_ONLY' WHERE username='admin';\"
subprocess.run(['psql', '-h', 'postgres', '-U', 'postgres', '-d', 'ipview', '-c', sql], env={**__import__('os').environ, 'PGPASSWORD': 'postgres'})
"
```

### Disable TOTP

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET totp_secret_encrypted=null, auth_mode='PASSWORD_ONLY' WHERE username='admin';"
```

### Switch Authentication Mode to Password Only

If a user is set to TOTP-only mode and can no longer log in:

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET auth_mode='PASSWORD_ONLY', totp_secret_encrypted=null WHERE username='admin';"
```

### Create a New Administrator

If all administrator accounts can no longer be recovered, you can create a new one directly:

```bash
docker exec -it ipview-backend-1 python -c "
from passlib.context import CryptContext
import subprocess, os
h = CryptContext(schemes=['bcrypt']).hash('admin123')
sql = f\"INSERT INTO users (id, username, password_hash, role, auth_mode, is_active, failed_login_attempts, created_at, updated_at) VALUES (gen_random_uuid(), 'newadmin', '{h}', 'admin', 'PASSWORD_ONLY', true, 0, now(), now()) ON CONFLICT (username) DO NOTHING;\"
subprocess.run(['psql', '-h', 'postgres', '-U', 'postgres', '-d', 'ipview', '-c', sql], env={**os.environ, 'PGPASSWORD': 'postgres'})
"
```

### Enable / Disable a User

Manually enable a disabled user:

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET is_active=true WHERE username='admin';"
```

Manually disable a user:

```bash
docker exec -it ipview-postgres-1 psql -U postgres -d ipview -c \
  "UPDATE users SET is_active=false WHERE username='test';"
```

## License

MIT
