/**
 * 将后端返回的 UTC 时间字符串转为本地时区显示
 * 后端使用 datetime.utcnow() 存储，返回的 ISO 字符串无时区标识
 * 需要追加 'Z' 让浏览器识别为 UTC 再转为本地时间
 */
export function formatDateTime(t?: string | null, fallback = '-'): string {
  if (!t) return fallback
  // 如果已经包含时区标识（Z 或 +/-），直接解析；否则追加 Z
  const iso = t.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(t) ? t : t + 'Z'
  return new Date(iso).toLocaleString('zh-CN')
}
