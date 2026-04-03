<template>
  <div class="ip-manage">
    <n-grid :cols="5" :x-gap="16" :y-gap="16" v-if="selectedSubnet">
      <!-- Left: Subnet list -->
      <n-gi :span="1">
        <n-card title="网段列表" size="small" :bordered="false">
          <template #header-extra>
            <n-button text @click="showAddSubnet = true"><n-icon><add-outline /></n-icon></n-button>
          </template>
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
        </n-card>
      </n-gi>

      <!-- Right: IP grid + stats -->
      <n-gi :span="4">
        <!-- Stats row -->
        <n-grid :cols="4" :x-gap="12" style="margin-bottom: 12px">
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

        <!-- Search -->
        <n-space style="margin-bottom: 12px">
          <n-input v-model:value="searchQ" placeholder="搜索 IP / MAC / 网段" clearable style="width: 300px" @keyup.enter="handleSearch">
            <template #prefix><n-icon><search-outline /></n-icon></template>
          </n-input>
          <n-button type="primary" @click="handleSearch">搜索</n-button>
        </n-space>

        <!-- IP Grid -->
        <n-card :bordered="false" size="small">
          <div class="ip-grid" v-if="!searchResult">
            <div
              v-for="ip in paginatedIPs"
              :key="ip.id"
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
          <!-- Pagination -->
          <n-pagination
            v-if="!searchResult && bulkData.total > 0"
            style="margin-top: 12px; justify-content: center"
            v-model:page="page"
            :page-size="pageSize"
            :page-sizes="[50, 100, 200]"
            :page-count="pageCount"
            @update:page="onPageChange"
          />
        </n-card>
      </n-gi>
    </n-grid>

    <!-- No subnet selected -->
    <n-empty v-else description="请从左侧选择一个网段" style="margin-top: 100px" />

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

const message = useMessage()

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
const pageSize = ref(200)
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
  page.value = 1
  try {
    const res = await api.get<IPBulkResponse>(`/ip/subnets/${sub.id}/ips`)
    bulkData.value = res.data
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
  if (!searchQ.value.trim()) { searchResult.value = null; return }
  try {
    const res = await api.get('/ip/search', { params: { q: searchQ.value } })
    if (res.data.type === 'ip') {
      searchResult.value = [res.data.record]
    } else if (res.data.type === 'mac' || res.data.type === 'subnet') {
      searchResult.value = res.data.records
    } else {
      searchResult.value = []
      message.info('未找到结果')
    }
  } catch (e) { message.error('搜索失败') }
}

async function showTooltip(ip: IPRecord, event: MouseEvent) {
  tooltipIP.value = ip
  tooltipStyle.top = (event.clientY + 10) + 'px'
  tooltipStyle.left = (event.clientX + 10) + 'px'
  tooltipVisible.value = true
  try {
    const res = await api.get<IPTooltipData>(`/ip/ip/${ip.ip_address}/tooltip`)
    tooltipHistory.value = res.data.history.map((h, i) => ({
      mac: h.mac_address,
      isCurrent: i === 0
    }))
  } catch { /* ignore */ }
}

function hideTooltip() { tooltipVisible.value = false }
function statusType(s?: string) { return s === 'ONLINE' ? 'success' : s === 'OFFLINE' ? 'warning' : 'default' }
function formatTime(t?: string) { return t ? new Date(t).toLocaleString('zh-CN') : '无记录' }
function onPageChange(p: number) { page.value = p }
</script>

<style scoped>
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
.ip-cell:hover { transform: scale(1.1); box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.ip-text { overflow: hidden; text-overflow: ellipsis; }
.ip-tooltip {
  position: fixed;
  z-index: 9999;
  background: rgba(20,28,49,0.98);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  padding: 12px;
  min-width: 220px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  pointer-events: none;
}
.tooltip-title { font-weight: 700; margin-bottom: 4px; }
.tooltip-row { font-size: 12px; margin: 2px 0; }
.tooltip-divider { font-size: 11px; margin-top: 6px; color: rgba(255,255,255,0.5); }
</style>
