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
          <n-input v-model:value="searchQ" placeholder="搜索 IP / MAC / 网段" clearable style="width: 300px" @keyup.enter="handleSearch" @clear="searchResult = null; fuzzySubnets = null">
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
              :style="{ gridColumn: `span 1` }"
              @mouseenter="showTooltip(ip, $event)"
              @mouseleave="hideTooltip"
            >
              <span class="ip-text">{{ ip.ip_address.split('.').pop() }}</span>
            </div>
          </div>
          <!-- Search result table -->
          <n-data-table v-else :columns="searchResultColumns" :data="searchResult" :bordered="false" size="small" />
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
    <div v-if="tooltipVisible" class="ip-tooltip" :style="tooltipStyle">
      <div class="tooltip-title">IP 地址：{{ tooltipIP?.ip_address }}</div>
      <n-tag :type="statusType(tooltipIP?.status)" size="small" style="margin-bottom: 6px">
        {{ tooltipIP?.status || 'UNUSED' }}
      </n-tag>
      <div class="tooltip-row">MAC：{{ tooltipIP?.mac_address || '未知' }}</div>
      <div class="tooltip-row">上次扫描：{{ formatTime(tooltipIP?.last_seen) }}</div>
      <div class="tooltip-divider">历史 MAC：</div>
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
const { isDark } = useThemeStore()

const subnets = ref<IPSubnet[]>([])
const selectedSubnet = ref<IPSubnet | null>(null)
const bulkData = ref({ subnet: '', total: 0, online: 0, offline: 0, unused: 0, records: [] as IPRecord[] })
const searchQ = ref('')
const searchResult = ref<IPRecord[] | null>(null)
const searchResultColumns = [
  { title: 'IP', key: 'ip_address' },
  { title: 'MAC', key: 'mac_address' },
  { title: '状态', key: 'status', render: (row: any) => h('n-tag', { type: statusType(row.status), size: 'small' }, { default: () => row.status }) },
  { title: '最后发现', key: 'last_seen', render: (row: any) => formatTime(row.last_seen) }
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
  if (!searchQ.value.trim()) { searchResult.value = null; fuzzySubnets.value = null; return }
  try {
    const res = await api.get('/ip/search', { params: { q: searchQ.value } })
    fuzzySubnets.value = null
    if (res.data.type === 'ip') {
      searchResult.value = [res.data.record]
    } else if (res.data.type === 'mac') {
      searchResult.value = res.data.records
    } else if (res.data.type === 'subnet') {
      // Find and switch to the subnet
      const targetSubnet = subnets.value.find(s => s.id === res.data.subnet_id)
      if (targetSubnet) {
        await selectSubnet(targetSubnet)
        searchResult.value = null
        message.success(`已切换到网段: ${targetSubnet.cidr}`)
      } else {
        message.error('网段未找到')
      }
    } else if (res.data.type === 'subnets') {
      // Multiple fuzzy matches, show selection list
      searchResult.value = null
      fuzzySubnets.value = res.data.subnets
    } else {
      searchResult.value = []
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
.ip-cell.online { background: rgba(24,160,88,0.7); color: #fff; }
.ip-cell.offline { background: rgba(250,173,20,0.7); color: #fff; }
.ip-cell.unused { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.3); }
.light-mode .ip-cell.unused { background: #e5e7eb; color: #6b7280; }
.ip-cell:hover { transform: scale(1.1); box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.ip-text { overflow: hidden; text-overflow: ellipsis; }

/* Tooltip */
.ip-tooltip {
  position: fixed;
  z-index: 9999;
  background: rgba(20,28,49,0.98);
  color: #e2e8f0;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  padding: 12px;
  min-width: 220px;
  max-width: 360px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  pointer-events: none;
}
.light-mode .ip-tooltip {
  background: rgba(255,255,255,0.98);
  border: 1px solid #d1d5db;
  color: #1f2937;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.tooltip-title { font-weight: 700; margin-bottom: 4px; }
.tooltip-row { font-size: 12px; margin: 2px 0; }
.tooltip-divider { font-size: 11px; margin-top: 6px; color: rgba(255,255,255,0.5); }
.light-mode .tooltip-divider { color: rgba(0,0,0,0.5); }

/* Subnet list card */
.subnet-list-card :deep(.n-card__content) { padding: 0 8px 0 8px; }
.subnet-list-card :deep(.n-thing-main__header) { font-size: 13px; }
.subnet-list-card :deep(.n-list-item) { padding-left: 8px; padding-right: 8px; }
.light-mode :deep(.n-thing-main__description) { color: #6b7280; }
</style>
