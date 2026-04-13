/**
 * 将后端返回的 UTC 时间字符串转为 Date 对象
 * 后端使用 datetime.utcnow() 存储，返回的 ISO 字符串无时区标识
 * 需要追加 'Z' 让浏览器识别为 UTC 再转为本地时间
 */
export function parseUTC(t?: string | null): Date | null {
  if (!t) return null
  const iso = t.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(t) ? t : t + 'Z'
  return new Date(iso)
}

/**
 * 将后端返回的 UTC 时间字符串转为本地时区显示
 */
export function formatDateTime(t?: string | null, fallback = '-'): string {
  const d = parseUTC(t)
  if (!d) return fallback
  return d.toLocaleString('zh-CN')
}
