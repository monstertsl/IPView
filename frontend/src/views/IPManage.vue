<template>
  <div class="ip-manage" :class="{ 'light-mode': !isDark }">
    <div class="ip-layout" v-if="selectedSubnet">
      <!-- Left: Subnet list -->
      <div class="ip-layout-left">
        <n-card title="网段列表" size="small" :bordered="false" class="subnet-list-card">
          <template #header-extra>
            <n-button text @click="showAddSubnet = true"><n-icon><add-outline /></n-icon></n-button>
          </template>
          <n-scrollbar style="height: calc(100vh - 152px);">
            <n-list hoverable clickable>
              <n-list-item
                v-for="sub in subnets"
                :key="sub.id"
                :style="{ background: selectedSubnet?.id === sub.id ? 'rgba(24,160,88,0.15)' : '' }"
                @click="selectSubnet(sub)"
              >
                <n-thing :title="sub.cidr" :description="sub.description" />
              </n-list-item>
            </n-list>
          </n-scrollbar>
        </n-card>
      </div>

      <!-- Right: IP grid + stats -->
      <div class="ip-layout-right">
        <!-- Search -->
        <n-space style="margin-bottom: 12px">
          <n-input v-model:value="searchQ" placeholder="搜索 IP / MAC / 网段" clearable style="width: 300px" @keyup.enter="handleSearch" @clear="searchResult = null; searchData = null; fuzzySubnets = null">
            <template #prefix><n-icon><search-outline /></n-icon></template>
          </n-input>
          <n-button type="primary" @click="handleSearch">搜索</n-button>
        </n-space>

        <!-- Subnet title + Stats (hide when searching IP/MAC or fuzzy matches) -->
        <n-grid v-if="!searchResult && !fuzzySubnets" :cols="5" :x-gap="12" style="margin-bottom: 12px; align-items: end;">
          <n-gi>
            <n-statistic label="网段" style="--n-label-font-size: 14px;">
              <template #default>
                <n-tag size="large" type="primary" style="font-size: 24px; font-weight: 600; padding: 4px 12px;">
                  {{ selectedSubnet?.cidr }}
                </n-tag>
              </template>
            </n-statistic>
          </n-gi>
          <n-gi><n-statistic label="在线 (ONLINE)" :value="bulkData.online">
            <template #suffix><n-tag type="success" size="small">使用中</n-tag></template>
          </n-statistic></n-gi>
          <n-gi><n-statistic label="离线 (OFFLINE)" :value="bulkData.offline">
            <template #suffix><n-tag type="warning" size="small">闲置</n-tag></template>
          </n-statistic></n-gi>
          <n-gi><n-statistic label="未用 (UNUSED)" :value="bulkData.unused">
            <template #suffix><n-tag type="default" size="small">空闲</n-tag></template>
          </n-statistic></n-gi>
          <n-gi><n-statistic label="总计" :value="bulkData.total" /></n-gi>
        </n-grid>

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
          <div class="ip-grid" v-else-if="!searchResult">
            <div
              v-for="ip in paginatedIPs"
              :key="ip.ip_address"
              class="ip-cell"
              :class="ip.status?.toLowerCase() || 'unused'"
              :style="cellStyle(ip.status)"
              @mouseenter="showTooltip(ip, $event)"
              @mouseleave="hideTooltip"
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
              <n-data-table v-if="searchData.history?.length" :columns="ipHistoryColumns" :data="searchData.history" :bordered="false" size="small" />
              <n-text v-else depth="3">无历史记录</n-text>
            </template>
            <!-- MAC search result -->
            <template v-else-if="searchData?.type === 'mac'">
              <n-descriptions :column="2" bordered size="small" label-placement="left" style="margin-bottom: 12px;">
                <n-descriptions-item label="MAC 地址">{{ searchQ }}</n-descriptions-item>
                <n-descriptions-item label="当前 IP">
                  <span v-for="(ip, i) in (searchData.current_ips || [])" :key="ip">
                    <n-tag type="success" size="small" style="margin-right: 4px;">{{ ip }}</n-tag>
                  </span>
                  <span v-if="!searchData.current_ips?.length">无</span>
                </n-descriptions-item>
              </n-descriptions>
              <n-text strong style="display:block; margin-bottom: 6px;">历史 IP 记录（最近 5 条）</n-text>
              <n-data-table v-if="searchData.history?.length" :columns="macHistoryColumns" :data="searchData.history" :bordered="false" size="small" />
              <n-text v-else depth="3">无历史记录</n-text>
            </template>
          </div>
        </n-card>
      </div>
    </div>

    <!-- No subnet selected -->
    <div v-else style="margin-top: 100px; text-align: center">
      <n-empty description="暂无网段，请先添加一个网段" />
      <n-button type="primary" style="margin-top: 16px" @click="showAddSubnet = true">
        <template #icon><n-icon><add-outline /></n-icon></template>
        添加网段
      </n-button>
    </div>

    <!-- Add subnet modal -->
    <n-modal v-model:show="showAddSubnet" preset="card" title="添加网段" style="width: 500px">
      <n-form :model="newSubnet" label-placement="top">
        <n-form-item label="CIDR" required>
          <n-input v-model:value="newSubnet.cidr" placeholder="如 10.10.0.0/24" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="newSubnet.description" placeholder="可选描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddSubnet = false">取消</n-button>
          <n-button type="primary" @click="addSubnet">确定</n-button>
        </n-space>
      </template>
    </n-modal>

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
      </div>
      <n-text v-else depth-3 >无历史记录</n-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { h } from 'vue'
import api from '@/api'
import type { IPSubnet, IPRecord, IPBulkResponse, IPTooltipData } from '@/types'
import { SearchOutline, AddOutline } from '@vicons/ionicons5'
import { formatDateTime } from '@/utils/time'
import { useThemeStore } from '@/stores/theme'

const message = useMessage()
const themeStore = useThemeStore()
const isDark = computed(() => themeStore.isDark)

const subnets = ref<IPSubnet[]>([])
const selectedSubnet = ref<IPSubnet | null>(null)
const bulkData = ref({ subnet: '', total: 0, online: 0, offline: 0, unused: 0, records: [] as IPRecord[] })
const searchQ = ref('')
const searchResult = ref<any | null>(null)  // kept for v-if in template
const searchData = ref<any | null>(null)

const ipHistoryColumns = [
  { title: 'MAC 地址', key: 'mac_address', render: (row: any) => {
    const isCurrent = searchData.value?.current_mac && row.mac_address.toUpperCase() === searchData.value.current_mac.toUpperCase()
    return h('span', { style: isCurrent ? { color: '#18a058', fontWeight: '600' } : {} }, 
      isCurrent ? `${row.mac_address} (当前)` : row.mac_address)
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

// Add subnet
const showAddSubnet = ref(false)
const newSubnet = reactive({ cidr: '', description: '' })

// Tooltip
const tooltipVisible = ref(false)
const tooltipIP = ref<IPRecord | null>(null)
const tooltipHistory = ref<{ mac: string; isCurrent: boolean }[]>([])
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
  await loadSubnets()
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

async function addSubnet() {
  try {
    await api.post('/ip/subnets', newSubnet)
    message.success('网段添加成功')
    showAddSubnet.value = false
    newSubnet.cidr = ''
    newSubnet.description = ''
    await loadSubnets()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '添加失败')
  }
}

async function handleSearch() {
  if (!searchQ.value.trim()) { searchResult.value = null; searchData.value = null; fuzzySubnets.value = null; return }
  try {
    const res = await api.get('/ip/search', { params: { q: searchQ.value } })
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
  // Only prefetch IPs that have been seen (have MAC) to save requests
  const active = records.filter(r => r.mac_address)
  for (const ip of active) {
    if (tooltipCache.value[ip.ip_address]) continue
    try {
      const res = await api.get<IPTooltipData>(`/ip/ip/${ip.ip_address}/tooltip`)
      tooltipCache.value[ip.ip_address] = res.data
    } catch { /* ignore */ }
  }
}

function showTooltip(ip: IPRecord, event: MouseEvent) {
  tooltipIP.value = ip
  tooltipVisible.value = true

  // 使用 nextTick 确保 tooltip 已渲染后再计算位置
  setTimeout(() => {
    const tooltipEl = document.querySelector('.ip-tooltip') as HTMLElement
    const tooltipWidth = tooltipEl?.offsetWidth || 220
    const tooltipHeight = tooltipEl?.offsetHeight || 150
    const padding = 10

    let top = event.clientY + padding
    let left = event.clientX + padding

    // 检测右边界
    if (left + tooltipWidth > window.innerWidth) {
      left = event.clientX - tooltipWidth - padding
    }
    // 检测下边界
    if (top + tooltipHeight > window.innerHeight) {
      top = event.clientY - tooltipHeight - padding
    }

    tooltipStyle.top = top + 'px'
    tooltipStyle.left = left + 'px'
  }, 0)

  // Use cached data if available, no request on hover
  const cached = tooltipCache.value[ip.ip_address]
  if (cached) {
    tooltipHistory.value = cached.history.map((h: any, i: number) => ({
      mac: h.mac_address,
      isCurrent: i === 0
    }))
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
  if (s === 'offline') return { background: 'rgba(250,173,20,0.7)', color: '#fff' }
  // unused
  return isDark.value
    ? { background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.35)' }
    : { background: '#e5e7eb', color: '#6b7280' }
}
</script>

<style scoped>
.ip-layout {
  display: flex;
  gap: 16px;
  height: calc(100vh - 96px);
  min-height: 0;
}
.ip-layout-left {
  width: 220px;
  min-width: 220px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ip-layout-left .subnet-list-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
}
.ip-layout-left :deep(.n-card__content) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.ip-layout-right {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  height: 100%;
}

/* IP Grid */
.ip-grid {
  display: grid;
  grid-template-columns: repeat(20, 1fr);
  gap: 4px;
}
.ip-cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.15s;
}
.ip-cell:hover { transform: scale(1.1); box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.ip-text { overflow: hidden; text-overflow: ellipsis; }

/* Tooltip */
.ip-tooltip {
  position: fixed;
  z-index: 9999;
  border-radius: 8px;
  padding: 12px;
  min-width: 220px;
  max-width: 360px;
  pointer-events: none;
}
.tooltip-title { font-weight: 700; margin-bottom: 4px; }
.tooltip-row { font-size: 12px; margin: 2px 0; }
.tooltip-divider { font-size: 11px; margin-top: 6px; }

/* Subnet list card */
.subnet-list-card :deep(.n-card__content) { padding: 0 8px 0 8px; }
.subnet-list-card :deep(.n-thing-main__header) { font-size: 13px; }
.subnet-list-card :deep(.n-list-item) { padding-left: 8px; padding-right: 8px; }

</style>
