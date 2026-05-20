<template>
  <div>
    <h1 class="page-title">📋 系统日志</h1>

    <!-- 统计概览 -->
    <div class="stats-grid" v-if="stats">
      <div class="card stat-card">
        <div class="stat-number">{{ stats.total || 0 }}</div>
        <div class="stat-label">总日志数</div>
      </div>
      <div class="card stat-card">
        <div class="stat-number" style="color:#e74c3c">{{ stats.by_level?.ERROR || 0 }}</div>
        <div class="stat-label">错误</div>
      </div>
      <div class="card stat-card">
        <div class="stat-number" style="color:#f39c12">{{ stats.by_level?.WARNING || 0 }}</div>
        <div class="stat-label">警告</div>
      </div>
      <div class="card stat-card">
        <div class="stat-number" style="color:#27ae60">{{ stats.by_level?.INFO || 0 }}</div>
        <div class="stat-label">信息</div>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="card">
      <div class="filter-bar">
        <select v-model="filters.level" @change="loadLogs" class="filter-select">
          <option value="">全部级别</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <input v-model="filters.logger" @input="debouncedLoad" placeholder="模块名过滤..." class="filter-input" />
        <input v-model="filters.search" @input="debouncedLoad" placeholder="搜索消息..." class="filter-input filter-input-wide" />
        <button @click="loadLogs" class="btn btn-primary btn-sm">🔍 查询</button>
        <button @click="refresh" class="btn btn-success btn-sm">🔄 刷新</button>
        <button @click="showClearConfirm = true" class="btn btn-danger btn-sm">🗑️ 清空</button>
      </div>
    </div>

    <!-- 日志列表 -->
    <div class="card">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else>
        <table>
          <thead>
            <tr>
              <th style="width:160px">时间</th>
              <th style="width:80px">级别</th>
              <th style="width:160px">模块</th>
              <th>消息</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id" :class="'log-row-' + log.level.toLowerCase()" @click="selectLog(log)">
              <td class="log-time">{{ formatTime(log.timestamp) }}</td>
              <td><span :class="'badge badge-level-' + log.level.toLowerCase()">{{ log.level }}</span></td>
              <td class="log-module">{{ log.logger }}</td>
              <td class="log-message">{{ log.message }}</td>
            </tr>
            <tr v-if="logs.length === 0">
              <td colspan="4" style="text-align:center;color:#888;padding:30px">暂无日志记录</td>
            </tr>
          </tbody>
        </table>

        <!-- 分页 -->
        <div class="pagination" v-if="total > filters.limit">
          <button @click="prevPage" :disabled="filters.offset === 0" class="btn btn-sm btn-primary">⬅ 上一页</button>
          <span class="page-info">{{ Math.floor(filters.offset / filters.limit) + 1 }} / {{ Math.ceil(total / filters.limit) }} 页 (共 {{ total }} 条)</span>
          <button @click="nextPage" :disabled="filters.offset + filters.limit >= total" class="btn btn-sm btn-primary">下一页 ➡</button>
        </div>
      </div>
    </div>

    <!-- 日志详情弹窗 -->
    <div v-if="selectedLog" class="modal-overlay" @click.self="selectedLog = null">
      <div class="modal" style="width:640px">
        <h3 class="modal-title">日志详情</h3>
        <div class="log-detail">
          <div class="detail-row"><span class="detail-label">时间:</span> {{ selectedLog.timestamp }}</div>
          <div class="detail-row"><span class="detail-label">级别:</span> <span :class="'badge badge-level-' + selectedLog.level.toLowerCase()">{{ selectedLog.level }}</span></div>
          <div class="detail-row"><span class="detail-label">模块:</span> {{ selectedLog.logger }}</div>
          <div class="detail-row"><span class="detail-label">函数:</span> {{ selectedLog.function }}:{{ selectedLog.line }}</div>
          <div class="detail-row"><span class="detail-label">消息:</span></div>
          <pre class="detail-message">{{ selectedLog.message }}</pre>
          <div v-if="selectedLog.exception">
            <div class="detail-row"><span class="detail-label">异常:</span></div>
            <pre class="detail-exception">{{ selectedLog.exception }}</pre>
          </div>
        </div>
        <div class="modal-actions">
          <button @click="selectedLog = null" class="btn btn-primary">关闭</button>
        </div>
      </div>
    </div>

    <!-- 清空确认 -->
    <div v-if="showClearConfirm" class="modal-overlay" @click.self="showClearConfirm = false">
      <div class="modal">
        <h3 class="modal-title">⚠️ 确认清空日志</h3>
        <p>此操作将删除所有日志记录，不可恢复。确定继续？</p>
        <div class="modal-actions">
          <button @click="showClearConfirm = false" class="btn">取消</button>
          <button @click="clearLogs" class="btn btn-danger">确认清空</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import api from '../api'

const logs = ref([])
const stats = ref(null)
const total = ref(0)
const loading = ref(false)
const error = ref(null)
const selectedLog = ref(null)
const showClearConfirm = ref(false)

const filters = reactive({
  level: '',
  logger: '',
  search: '',
  limit: 50,
  offset: 0,
})

let debounceTimer = null
let autoRefreshTimer = null

function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    filters.offset = 0
    loadLogs()
  }, 400)
}

async function loadLogs() {
  loading.value = true
  error.value = null
  try {
    const params = {}
    if (filters.level) params.level = filters.level
    if (filters.logger) params.logger = filters.logger
    if (filters.search) params.search = filters.search
    params.limit = filters.limit
    params.offset = filters.offset

    const res = await api.queryLogs(params)
    logs.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    error.value = '加载日志失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const res = await api.getLogStats()
    stats.value = res.data
  } catch (e) {
    // 静默失败
  }
}

function refresh() {
  loadLogs()
  loadStats()
}

async function clearLogs() {
  try {
    await api.clearLogs()
    showClearConfirm.value = false
    refresh()
  } catch (e) {
    error.value = '清空失败: ' + (e.response?.data?.detail || e.message)
    showClearConfirm.value = false
  }
}

function selectLog(log) {
  selectedLog.value = log
}

function prevPage() {
  filters.offset = Math.max(0, filters.offset - filters.limit)
  loadLogs()
}

function nextPage() {
  filters.offset += filters.limit
  loadLogs()
}

function formatTime(ts) {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return ts
  }
}

onMounted(() => {
  refresh()
  // 每 10 秒自动刷新
  autoRefreshTimer = setInterval(refresh, 10000)
})

onUnmounted(() => {
  clearInterval(autoRefreshTimer)
  clearTimeout(debounceTimer)
})
</script>

<style scoped>
.filter-bar {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
}
.filter-select {
  padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9em; min-width: 120px;
}
.filter-input {
  padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9em; width: 140px;
}
.filter-input-wide { width: 200px; }

.log-time { font-family: monospace; font-size: 0.85em; color: #666; white-space: nowrap; }
.log-module { font-family: monospace; font-size: 0.85em; color: #555; }
.log-message { font-size: 0.9em; max-width: 500px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

tr { cursor: pointer; }

.log-row-error { background: #fff5f5; }
.log-row-warning { background: #fffdf5; }
.log-row-critical { background: #ffe0e0; }

.badge-level-debug { background: #e8f4fd; color: #1976d2; }
.badge-level-info { background: #d4edda; color: #155724; }
.badge-level-warning { background: #fff3cd; color: #856404; }
.badge-level-error { background: #f8d7da; color: #721c24; }
.badge-level-critical { background: #d32f2f; color: #fff; }

.pagination {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  padding: 16px 0 4px; border-top: 1px solid #eee; margin-top: 8px;
}
.page-info { font-size: 0.9em; color: #666; }

.log-detail { font-size: 0.9em; }
.detail-row { margin-bottom: 8px; }
.detail-label { font-weight: 600; color: #555; margin-right: 8px; }
.detail-message {
  background: #f8f9fa; padding: 12px; border-radius: 6px;
  font-size: 0.9em; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto;
}
.detail-exception {
  background: #fff5f5; padding: 12px; border-radius: 6px; color: #c0392b;
  font-size: 0.85em; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto;
}
</style>
