<template>
  <div class="ip-manage" :class="{ 'light-mode': !isDark }">
    <div class="ip-layout" v-if="selectedSubnet">
      <div class="ip-body">
        <!-- Toolbar: 搜索 IP / MAC / 网段（输入自动补全，选网段可直接切换） -->
        <div class="ip-toolbar">
          <n-auto-complete
            v-model:value="searchQ"
            :options="searchSuggestions"
            class="ip-search-input"
            @select="onSelectSuggestion"
          >
            <template #default="{ handleInput, handleBlur, handleFocus, value }">
              <n-input
                :value="value"
                placeholder="搜索 IP / MAC / 网段"
                clearable
                @input="handleInput"
                @focus="handleFocus"
                @blur="handleBlur"
                @keyup.enter="handleSearch"
                @clear="searchResult = null; searchData = null; fuzzySubnets = null"
              >
                <template #prefix><n-icon><search-outline /></n-icon></template>
              </n-input>
            </template>
          </n-auto-complete>
          <n-button type="primary" @click="handleSearch">搜索</n-button>
        </div>

        <!-- Subnet title + Stats (hide when searching IP/MAC or fuzzy matches) -->
        <div v-if="!searchResult && !fuzzySubnets" class="subnet-stats">
          <div class="stat-item">
            <n-statistic label="网段">
              <template #default>
                <n-tag size="large" type="primary" style="font-size: 20px; font-weight: 600; padding: 2px 10px;">
                  {{ selectedSubnet?.cidr }}
                </n-tag>
              </template>
            </n-statistic>
          </div>
          <div class="stat-item">
            <n-statistic label="在线 (ONLINE)" :value="bulkData.online">
              <template #suffix><n-tag type="success" size="small">使用中</n-tag></template>
            </n-statistic>
          </div>
          <div class="stat-item">
            <n-statistic label="离线 (OFFLINE)" :value="bulkData.offline">
              <template #suffix><n-tag type="warning" size="small">离线</n-tag></template>
            </n-statistic>
          </div>
          <div class="stat-item">
            <n-statistic label="未使用 (UNUSED)" :value="bulkData.unused">
              <template #suffix><n-tag type="default" size="small">空闲</n-tag></template>
            </n-statistic>
          </div>
          <div class="stat-item">
            <n-statistic label="总计" :value="bulkData.total" />
          </div>
        </div>

        <!-- IP Grid -->
        <n-card :bordered="false" size="small">
          <!-- Fuzzy subnet matches -->
          <div v-if="fuzzySubnets" style="padding: 8px 0;">
            <n-text depth="3" style="margin-bottom: 8px; display: block;">找到 {{ fuzzySubnets.length }} 个匹配网段，请选择：</n-text>
            <n-space vertical :size="4">
              <n-button
                v-for="item in fuzzySubnets"
                :key="item.subnet_id"
                text
                type="primary"
                style="font-size: 14px;"
                @click="selectFuzzySubnet(item)"
              >
                {{ item.cidr }}
              </n-button>
            </n-space>
          </div>
          <div class="ip-grid" v-else-if="!searchResult" ref="gridEl" :style="{ gridTemplateColumns: `repeat(${gridCols}, minmax(0, 1fr))`, fontSize: cellFontSize + 'px' }">
            <div
              v-for="ip in paginatedIPs"
              :key="ip.ip_address"
              class="ip-cell"
              :class="ip.status?.toLowerCase() || 'unused'"
              :style="cellStyle(ip.status)"
              @pointerenter="onCellEnter(ip, $event)"
              @pointerleave="onCellLeave"
              @click="onCellClick(ip, $event)"
            >
              <span class="ip-text">{{ ip.ip_address.split('.').pop() }}</span>
            </div>
          </div>
          <!-- Search result -->
          <div v-else class="search-result-detail">
            <!-- IP search result -->
            <template v-if="searchData?.type === 'ip'">
              <n-descriptions :column="2" bordered size="small" label-placement="left" style="margin-bottom: 12px;">
                <n-descriptions-item label="IP 地址">{{ searchData.record.ip_address }}</n-descriptions-item>
                <n-descriptions-item label="状态"><n-tag :type="statusType(searchData.record.status)" size="small">{{ searchData.record.status || 'UNUSED' }}</n-tag></n-descriptions-item>
                <n-descriptions-item label="当前 MAC">{{ searchData.record.mac_address || '无' }}</n-descriptions-item>
                <n-descriptions-item label="最后发现">{{ formatTime(searchData.record.last_seen) }}</n-descriptions-item>
              </n-descriptions>
              <n-text strong style="display:block; margin-bottom: 6px;">历史 MAC 记录（最近 5 条）</n-text>
              <n-data-table v-if="ipSearchHistory.length" :columns="ipHistoryColumns" :data="ipSearchHistory" :bordered="false" size="small" />
              <n-text v-else depth="3">无历史记录</n-text>
            </template>
            <!-- MAC search result -->
            <template v-else-if="searchData?.type === 'mac'">
              <n-descriptions :column="2" bordered size="small" label-placement="left" style="margin-bottom: 12px;">
                <n-descriptions-item label="MAC 地址">{{ normalizedQuery }}</n-descriptions-item>
                <n-descriptions-item label="当前 IP">
                  <span v-for="(ip, i) in (searchData.current_ips || [])" :key="ip">
                    <n-tag type="success" size="small" style="margin-right: 4px;">{{ ip }}</n-tag>
                  </span>
                  <span v-if="!searchData.current_ips?.length">无</span>
                </n-descriptions-item>
              </n-descriptions>
              <n-text strong style="display:block; margin-bottom: 6px;">历史 IP 记录（最近 5 条）</n-text>
              <n-data-table v-if="macSearchHistory.length" :columns="macHistoryColumns" :data="macSearchHistory" :bordered="false" size="small" />
              <n-text v-else depth="3">无历史记录</n-text>
            </template>
          </div>
        </n-card>
      </div>
    </div>

    <!-- No subnet selected -->
    <div v-else style="margin-top: 100px; text-align: center">
      <n-empty description="暂无网段，扫描任务执行后会自动发现网段" />
      <n-button style="margin-top: 16px" @click="goScan">
        <template #icon><n-icon><search-outline /></n-icon></template>
        前往扫描管理
      </n-button>
    </div>

    <!-- Tooltip -->
    <div v-if="tooltipVisible" class="ip-tooltip" :style="[tooltipStyle, tooltipThemeStyle]">
      <div class="tooltip-title">IP 地址：{{ tooltipIP?.ip_address }}</div>
      <n-tag :type="statusType(tooltipIP?.status)" size="small" style="margin-bottom: 6px">
        {{ tooltipIP?.status || 'UNUSED' }}
      </n-tag>
      <div class="tooltip-row">MAC：{{ tooltipIP?.mac_address || '未知' }}</div>
      <div class="tooltip-row">上次扫描：{{ formatTime(tooltipIP?.last_seen) }}</div>
      <div class="tooltip-divider" :style="tooltipDividerStyle">历史 MAC：</div>
      <div v-if="tooltipHistory.length" v-for="h in tooltipHistory" :key="h.id" class="tooltip-row" :style="{ color: h.isCurrent ? '#18a058' : '' }">
        {{ h.mac }}
        <span v-if="h.isCurrent" style="color:#18a058">(当前)</span>
        <span v-else-if="h.isLast">(最后)</span>
      </div>
      <n-text v-else depth-3 >无历史记录</n-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import { h } from 'vue'
import api from '@/api'
import type { IPSubnet, IPRecord, IPBulkResponse, IPTooltipData } from '@/types'
import { useRouter } from 'vue-router'
import { SearchOutline } from '@vicons/ionicons5'
import { formatDateTime } from '@/utils/time'
import { useThemeStore } from '@/stores/theme'

const message = useMessage()
const themeStore = useThemeStore()
const isDark = computed(() => themeStore.isDark)

// Dynamic grid columns based on container width
const gridCols = ref(20)
const gridEl = ref<HTMLElement | null>(null)
const cellFontSize = ref(14)
let gridResizeObserver: ResizeObserver | null = null

function updateGrid() {
  const width = gridEl.value?.clientWidth || Math.max(320, window.innerWidth - 40)
  // 小屏用更小的目标格宽，保证格子足够大以容纳三位数尾数
  const targetCell = width < 700 ? 26 : 46
  const cols = Math.max(8, Math.floor((width + 4) / (targetCell + 4)))
  gridCols.value = Math.min(32, cols)
  // 字体随格子实际宽度缩放（桌面上限 18px，避免大格子配小字）
  const cellW = (width - (gridCols.value - 1) * 4) / gridCols.value
  cellFontSize.value = Math.max(9, Math.min(18, Math.floor(cellW * 0.5)))
}

// 网格元素随 v-if 挂载/卸载，挂载后用 ResizeObserver 跟踪实际宽度
watch(gridEl, (el) => {
  gridResizeObserver?.disconnect()
  if (el) {
    gridResizeObserver = new ResizeObserver(() => updateGrid())
    gridResizeObserver.observe(el)
    updateGrid()
  }
})

const subnets = ref<IPSubnet[]>([])
const selectedSubnet = ref<IPSubnet | null>(null)
const bulkData = ref({ subnet: '', total: 0, online: 0, offline: 0, unused: 0, records: [] as IPRecord[] })
const searchQ = ref('')
const normalizedQuery = ref('')
const searchResult = ref<any | null>(null)  // kept for v-if in template
const searchData = ref<any | null>(null)

// Filtered history lists for the search panel.
// IP_RELEASED is an internal lifecycle marker — it carries the same MAC as the
// preceding NEW/MAC_CHANGED event, so showing it would just produce a visual
// duplicate. We hide it from search tables; the underlying event row remains
// in the database for auditing.
const ipSearchHistory = computed(() =>
  (searchData.value?.history || []).filter((h: any) => h.event_type !== 'IP_RELEASED')
)
const macSearchHistory = computed(() =>
  (searchData.value?.history || []).filter((h: any) => h.event_type !== 'IP_RELEASED')
)

const ipHistoryColumns = [
  { title: 'MAC 地址', key: 'mac_address', render: (row: any, rowIndex: number) => {
    const isCurrent = searchData.value?.current_mac && row.mac_address.toUpperCase() === searchData.value.current_mac.toUpperCase()
    const isUnused = searchData.value?.record?.status === 'UNUSED'
    const isLast = !isCurrent && isUnused && rowIndex === 0
    let suffix = ''
    if (isCurrent) suffix = ' (当前)'
    else if (isLast) suffix = ' (最后)'
    return h('span', { style: isCurrent ? { color: '#18a058', fontWeight: '600' } : {} },
      `${row.mac_address}${suffix}`)
  }},
  { title: '事件', key: 'event_type', width: 120 },
  { title: '时间', key: 'seen_at', width: 180, render: (row: any) => formatTime(row.seen_at) },
]

const macHistoryColumns = [
  { title: 'IP 地址', key: 'ip_address', render: (row: any) => {
    const isCurrent = (searchData.value?.current_ips || []).includes(row.ip_address)
    return h('span', { style: isCurrent ? { color: '#18a058', fontWeight: '600' } : {} },
      isCurrent ? `${row.ip_address} (当前)` : row.ip_address)
  }},
  { title: '事件', key: 'event_type', width: 120 },
  { title: '时间', key: 'seen_at', width: 180, render: (row: any) => formatTime(row.seen_at) },
]

// Pagination
const page = ref(1)
const pageSize = ref(256)
const pageCount = computed(() => Math.ceil(bulkData.value.total / pageSize.value))
const paginatedIPs = computed(() => bulkData.value.records.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

const router = useRouter()
function goScan() { router.push('/scan') }

// Tooltip
const tooltipVisible = ref(false)
const tooltipIP = ref<IPRecord | null>(null)
const tooltipHistory = ref<{ mac: string; isCurrent: boolean; isLast: boolean }[]>([])
const tooltipStyle = reactive({ top: '0px', left: '0px' })

const tooltipThemeStyle = computed(() => isDark.value
  ? { background: 'rgba(20,28,49,0.98)', color: '#e2e8f0', border: '1px solid rgba(255,255,255,0.12)', boxShadow: '0 4px 20px rgba(0,0,0,0.5)' }
  : { background: 'rgba(255,255,255,0.98)', color: '#1f2937', border: '1px solid #d1d5db', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }
)

const tooltipDividerStyle = computed(() => isDark.value
  ? { color: 'rgba(255,255,255,0.5)' }
  : { color: 'rgba(0,0,0,0.5)' }
)

onMounted(async () => {
  updateGrid()
  window.addEventListener('resize', updateGrid)
  document.addEventListener('click', onDocClick)
  await loadSubnets()
})

onUnmounted(() => {
  window.removeEventListener('resize', updateGrid)
  document.removeEventListener('click', onDocClick)
  gridResizeObserver?.disconnect()
})

async function loadSubnets() {
  try {
    const res = await api.get<IPSubnet[]>('/ip/subnets')
    subnets.value = res.data
    if (subnets.value.length > 0) {
      await selectSubnet(subnets.value[0])
    }
  } catch (e) { message.error('加载网段失败') }
}

async function selectSubnet(sub: IPSubnet) {
  selectedSubnet.value = sub
  searchResult.value = null
  searchData.value = null
  tooltipCache.value = {}  // clear cache on subnet switch
  try {
    const res = await api.get<IPBulkResponse>(`/ip/subnets/${sub.id}/ips`)
    bulkData.value = res.data
    // Prefetch tooltip data in background after subnet loads
    prefetchTooltips(res.data.records)
  } catch (e) { message.error('加载 IP 数据失败') }
}

// 搜索框自动补全：网段 CIDR + 当前网段的 IP / MAC
// （候选来自已加载的数据，无需额外请求）
const suggestionSource = computed(() => {
  const out: { text: string; type: string }[] = []
  const seen = new Set<string>()
  const add = (text?: string, type?: string) => {
    if (!text) return
    const key = text.toLowerCase()
    if (seen.has(key)) return
    seen.add(key)
    out.push({ text, type })
  }
  subnets.value.forEach(s => add(s.cidr, '网段'))
  bulkData.value.records.forEach(r => {
    add(r.ip_address, 'IP')
    add(r.mac_address || '', 'MAC')
  })
  return out
})

const searchSuggestions = computed(() => {
  const q = searchQ.value.trim().toLowerCase()
  if (!q) return []
  const starts: { text: string; type: string }[] = []
  const contains: { text: string; type: string }[] = []
  for (const item of suggestionSource.value) {
    const t = item.text.toLowerCase()
    if (t.startsWith(q)) {
      starts.push(item)
      if (starts.length >= 12) break
    } else if (t.includes(q) && contains.length < 12) {
      contains.push(item)
    }
  }
  // 前缀匹配的排在前面，其次是包含匹配
  return [...starts, ...contains].slice(0, 12).map(i => ({ label: `${i.text}  (${i.type})`, value: i.text }))
})

function onSelectSuggestion(value: string | number) {
  searchQ.value = String(value)
  handleSearch()
}

async function handleSearch() {
  if (!searchQ.value.trim()) { searchResult.value = null; searchData.value = null; fuzzySubnets.value = null; return }
  // Normalize MAC input: accept ':' / '-' separators in any case, emit the
  // canonical upper-case colon form used by the backend. Non-MAC queries
  // (IP / CIDR) are just trimmed.
  const raw = searchQ.value.trim()
  const macMatch = /^[0-9A-Fa-f]{2}([:\-][0-9A-Fa-f]{2}){5}$/.test(raw)
  const query = macMatch ? raw.replace(/-/g, ':').toUpperCase() : raw
  normalizedQuery.value = query
  try {
    const res = await api.get('/ip/search', { params: { q: query } })
    fuzzySubnets.value = null
    if (res.data.type === 'ip' || res.data.type === 'mac') {
      searchData.value = res.data
      searchResult.value = res.data  // truthy to trigger v-else
    } else if (res.data.type === 'subnet') {
      // Find and switch to the subnet
      const targetSubnet = subnets.value.find(s => s.id === res.data.subnet_id)
      if (targetSubnet) {
        await selectSubnet(targetSubnet)
        searchResult.value = null
        searchData.value = null
        message.success(`已切换到网段: ${targetSubnet.cidr}`)
      } else {
        message.error('网段未找到')
      }
    } else if (res.data.type === 'subnets') {
      // Multiple fuzzy matches, show selection list
      searchResult.value = null
      searchData.value = null
      fuzzySubnets.value = res.data.subnets
    } else {
      searchResult.value = null
      searchData.value = null
      fuzzySubnets.value = null
      message.info('未找到结果')
    }
  } catch (e) { message.error('搜索失败') }
}

// Fuzzy subnet matches
const fuzzySubnets = ref<{ subnet_id: string; cidr: string }[] | null>(null)

async function selectFuzzySubnet(item: { subnet_id: string; cidr: string }) {
  const targetSubnet = subnets.value.find(s => s.id === item.subnet_id)
  if (targetSubnet) {
    await selectSubnet(targetSubnet)
    fuzzySubnets.value = null
    searchResult.value = null
    message.success(`已切换到网段: ${targetSubnet.cidr}`)
  }
}

// Tooltip cache: ip_address → { history, last_seen, ... }
const tooltipCache = ref<Record<string, IPTooltipData>>({})

// Prefetch tooltip data for all IPs in the current subnet (fire and forget)
async function prefetchTooltips(records: IPRecord[]) {
  // Prefetch every IP that actually exists in the DB (id is non-empty).
  // We don't gate on mac_address because UNUSED rows have a NULL mac but still
  // carry meaningful event history (NEW / MAC_CHANGED / IP_RELEASED).
  const active = records.filter(r => r.id)
  for (const ip of active) {
    if (tooltipCache.value[ip.ip_address]) continue
    try {
      const res = await api.get<IPTooltipData>(`/ip/ip/${ip.ip_address}/tooltip`)
      tooltipCache.value[ip.ip_address] = res.data
    } catch { /* ignore */ }
  }
}

// 当前「真实可见区域」：移动端页面往往比屏幕宽（可横向滚动/被缩放），
// window.innerWidth 拿到的是整页布局视口，直接用会让 tooltip 跑到可视区外。
// visualViewport 给出的是用户此刻真正看到的那块矩形（同坐标系，可直接用）。
function getVisibleArea() {
  const vv = window.visualViewport
  if (vv) {
    return {
      left: vv.offsetLeft,
      top: vv.offsetTop,
      right: vv.offsetLeft + vv.width,
      bottom: vv.offsetTop + vv.height,
    }
  }
  return { left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight }
}

function positionTooltip(clientX: number, clientY: number) {
  setTimeout(() => {
    const tooltipEl = document.querySelector('.ip-tooltip') as HTMLElement
    const tooltipWidth = tooltipEl?.offsetWidth || 220
    const tooltipHeight = tooltipEl?.offsetHeight || 150
    const padding = 10
    const area = getVisibleArea()

    // 可用区间（始终收在可见区域内部，绝不越界）
    const minLeft = area.left + padding
    const maxLeft = Math.max(minLeft, area.right - tooltipWidth - padding)
    const minTop = area.top + padding
    const maxTop = Math.max(minTop, area.bottom - tooltipHeight - padding)

    // 水平：和鼠标一致，优先放在点击点右侧，右侧放不下再翻到左侧
    let left = clientX + padding
    if (left + tooltipWidth + padding > area.right) {
      left = clientX - tooltipWidth - padding
    }
    left = Math.min(Math.max(left, minLeft), maxLeft)

    // 垂直：优先放在点击点下方，下方放不下再翻到上方
    let top = clientY + padding
    if (top + tooltipHeight + padding > area.bottom) {
      top = clientY - tooltipHeight - padding
    }
    top = Math.min(Math.max(top, minTop), maxTop)

    tooltipStyle.top = top + 'px'
    tooltipStyle.left = left + 'px'
  }, 0)
}

// mouse 事件统一走 pointer 事件；touch 的 pointerenter 会被过滤，
// 触摸屏用户通过 click 显示/切换 tooltip，点击空白处关闭
function onCellEnter(ip: IPRecord, e: PointerEvent) {
  if (e.pointerType !== 'mouse') return
  showTooltip(ip, e.clientX, e.clientY)
}

function onCellLeave(e: PointerEvent) {
  // 触摸抬起后也会派发 pointerleave，若此时隐藏会导致 click 刚显示的 tooltip 闪没
  if (e.pointerType !== 'mouse') return
  hideTooltip()
}

function onCellClick(ip: IPRecord, e: MouseEvent) {
  // 同一 IP 已显示（如鼠标 hover 已展示）则保持不变
  if (tooltipVisible.value && tooltipIP.value?.ip_address === ip.ip_address) return
  // 触摸点击与鼠标 hover 使用同一套定位逻辑
  showTooltip(ip, e.clientX, e.clientY)
}

function onDocClick(e: MouseEvent) {
  const target = e.target as Element | null
  if (!target?.closest?.('.ip-cell')) hideTooltip()
}

function showTooltip(ip: IPRecord, clientX: number, clientY: number) {
  tooltipIP.value = ip
  tooltipVisible.value = true
  positionTooltip(clientX, clientY)

  // Use cached data if available, otherwise lazily fetch in the background
  // and render once it arrives. This covers IPs missed by the bulk prefetch.
  const renderHistory = (data: IPTooltipData) => {
    // Filter out IP_RELEASED events — they are an internal lifecycle marker,
    // not a "device MAC" event. The remaining list is the actual sequence of
    // devices that occupied this IP.
    const liveEvents = (data.history || []).filter((h: any) => h.event_type !== 'IP_RELEASED')
    const isUnused = data.status === 'UNUSED'
    tooltipHistory.value = liveEvents.map((h: any, i: number) => ({
      mac: h.mac_address,
      isCurrent: i === 0 && !isUnused,
      isLast: i === 0 && isUnused,
    }))
  }

  const cached = tooltipCache.value[ip.ip_address]
  if (cached) {
    renderHistory(cached)
  } else if (ip.id) {
    // Only fetch IPs that actually exist in the DB (id non-empty);
    // pristine subnet slots have id="" and have nothing to show.
    tooltipHistory.value = []
    api.get<IPTooltipData>(`/ip/ip/${ip.ip_address}/tooltip`)
      .then(res => {
        tooltipCache.value[ip.ip_address] = res.data
        // Only render if the user is still hovering this IP
        if (tooltipIP.value?.ip_address === ip.ip_address) renderHistory(res.data)
      })
      .catch(() => { /* ignore */ })
  } else {
    tooltipHistory.value = []
  }
}

function hideTooltip() { tooltipVisible.value = false }
function statusType(s?: string) { return s === 'ONLINE' ? 'success' : s === 'OFFLINE' ? 'warning' : 'default' }
function formatTime(t?: string) { return formatDateTime(t, '无记录') }

function cellStyle(status?: string) {
  const s = status?.toLowerCase() || 'unused'
  if (s === 'online') return { background: 'rgba(24,160,88,0.7)', color: '#fff' }
  if (s === 'offline') return { background: '#f0a020', color: '#fff' }
  // unused
  return isDark.value
    ? { background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.35)' }
    : { background: '#e5e7eb', color: '#6b7280' }
}
</script>

<style scoped>
.ip-layout {
  height: calc(100vh - 96px);
  min-height: 0;
  overflow-y: auto;
}

/* Toolbar: 搜索 */
.ip-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.ip-search-input {
  flex: 1 1 200px;
  min-width: 140px;
  max-width: 320px;
}

/* IP Grid */
.ip-grid {
  display: grid;
  gap: 4px;
}

/* Subnet stats */
.subnet-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 0;
  align-items: end;
  margin-bottom: 12px;
}
.stat-item {
  flex: 1 0 auto;
  min-width: 120px;
}
.ip-cell {
  aspect-ratio: 1;
  min-width: 0;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  font-size: inherit;
  font-weight: 500;
  transition: all 0.15s;
  overflow: hidden;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .ip-cell:hover { transform: scale(1.1); box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
}
.ip-text {
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Tooltip */
.ip-tooltip {
  position: fixed;
  z-index: 9999;
  border-radius: 8px;
  padding: 12px;
  min-width: 220px;
  max-width: min(360px, calc(100vw - 24px));
  pointer-events: none;
}
.tooltip-title { font-weight: 700; margin-bottom: 4px; }
.tooltip-row { font-size: 12px; margin: 2px 0; }
.tooltip-divider { font-size: 11px; margin-top: 6px; }

</style>
