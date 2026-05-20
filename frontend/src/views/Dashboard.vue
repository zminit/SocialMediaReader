<template>
  <div>
    <h1 class="page-title">📊 系统仪表盘</h1>

    <div v-if="error" class="error">{{ error }}</div>

    <!-- 健康状态 -->
    <div class="card" style="margin-bottom: 20px">
      <div class="card-title">系统状态</div>
      <div v-if="health" style="display: flex; gap: 16px; flex-wrap: wrap">
        <span class="badge" :class="health.status === 'healthy' ? 'badge-green' : 'badge-yellow'">
          {{ health.status === 'healthy' ? '✅ 正常' : '⚠️ 降级' }}
        </span>
        <span class="badge" :class="health.checks?.storage ? 'badge-green' : 'badge-red'">
          存储: {{ health.checks?.storage ? '✓' : '✗' }}
        </span>
        <span class="badge" :class="health.checks?.collector_available ? 'badge-green' : 'badge-yellow'">
          采集器: {{ health.checks?.collector_available ? '✓' : '未配置' }}
        </span>
        <span class="badge" :class="health.checks?.dify_available ? 'badge-green' : 'badge-yellow'">
          Dify: {{ health.checks?.dify_available ? '✓' : '未配置' }}
        </span>
        <span class="badge" :class="health.checks?.scheduler_running ? 'badge-green' : 'badge-yellow'">
          调度器: {{ health.checks?.scheduler_running ? '运行中' : '未启动' }}
        </span>
      </div>
      <div v-else class="loading">加载中...</div>
    </div>

    <!-- 统计数据 -->
    <div class="stats-grid">
      <div class="card stat-card">
        <div class="stat-number">{{ stats?.sources?.total ?? '-' }}</div>
        <div class="stat-label">采集内容总数</div>
      </div>
      <div class="card stat-card">
        <div class="stat-number">{{ stats?.sources?.by_status?.analyzed ?? '-' }}</div>
        <div class="stat-label">已分析</div>
      </div>
      <div class="card stat-card">
        <div class="stat-number">{{ stats?.sources?.by_status?.pending_analysis ?? '-' }}</div>
        <div class="stat-label">待分析</div>
      </div>
      <div class="card stat-card">
        <div class="stat-number">{{ stats?.duplicates?.total ?? '-' }}</div>
        <div class="stat-label">去重数</div>
      </div>
      <div class="card stat-card">
        <div class="stat-number">{{ stats?.filtered?.total ?? '-' }}</div>
        <div class="stat-label">过滤数</div>
      </div>
      <div class="card stat-card">
        <div class="stat-number">{{ stats?.pipeline_total ?? '-' }}</div>
        <div class="stat-label">管道总处理</div>
      </div>
    </div>

    <!-- 按状态分布 -->
    <div class="card" v-if="stats?.sources?.by_status">
      <div class="card-title">内容状态分布</div>
      <table>
        <thead><tr><th>状态</th><th>数量</th></tr></thead>
        <tbody>
          <tr v-for="(count, status) in stats.sources.by_status" :key="status">
            <td>
              <span class="badge" :class="statusBadge(status)">{{ status }}</span>
            </td>
            <td>{{ count }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const health = ref(null)
const stats = ref(null)
const error = ref('')

function statusBadge(s) {
  if (s === 'analyzed') return 'badge-green'
  if (s === 'pending_analysis') return 'badge-yellow'
  if (s === 'analysis_failed') return 'badge-red'
  return 'badge-blue'
}

onMounted(async () => {
  try {
    const [h, s] = await Promise.all([api.health(), api.getStats()])
    health.value = h.data
    stats.value = s.data
  } catch (e) {
    error.value = '无法连接后端 API，请确保 API 服务已启动 (uvicorn api.app:app)'
  }
})
</script>
