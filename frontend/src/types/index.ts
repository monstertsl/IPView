export interface User {
  id: string
  username: string
  role: 'admin' | 'user'
  auth_mode: string
  is_active: boolean
  totp_enabled: boolean
  failed_login_attempts: number
  last_login_at?: string
  created_at: string
}

export interface IPSubnet {
  id: string
  cidr: string
  description?: string
  created_at: string
}

export interface IPRecord {
  id: string
  ip_address: string
  mac_address?: string
  last_seen?: string
  status?: 'ONLINE' | 'OFFLINE' | 'UNUSED'
  created_at: string
}

export interface IPHistoryRecord {
  id: string
  ip_address: string
  mac_address: string
  event_type: string
  seen_at: string
}

export interface IPTooltipData {
  ip_address: string
  status: string
  current_mac?: string
  last_seen?: string
  history: IPHistoryRecord[]
}

export interface IPBulkResponse {
  subnet: string
  total: number
  online: number
  offline: number
  unused: number
  records: IPRecord[]
}

export interface Switch {
  id: string
  ip: string
  mac?: string
  snmp_version: string
  community?: string
  snmp_v3_config?: any
  location?: string
  description?: string
  is_active: boolean
}

export interface ScanTask {
  id: string
  status: string
  started_at?: string
  finished_at?: string
  duration?: number
  total_ips: number
  updated_ips: number
  error_message?: string
  triggered_by: string
  created_at: string
}

export interface ScanSubnet {
  id: string
  cidr: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at?: string
}
