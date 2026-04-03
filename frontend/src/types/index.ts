export interface User {
  id: string
  username: string
  role: 'admin' | 'user'
  auth_mode: string
  is_active: boolean
  totp_enabled: boolean
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
