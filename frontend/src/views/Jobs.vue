<template>
  <div>
    <h1 class="page-title">⚙️ 任务调度</h1>

    <div v-if="error" class="error">{{ error }}</div>

    <!-- 调度器状态 -->
    <div class="card">
      <div class="card-title">调度器状态</div>
      <div v-if="status" style="display:flex; gap:16px; flex-wrap:wrap">
        <span class="badge" :class="status.running ? 'badge-green' : 'badge-yellow'">
          {{ status.running ? '✅ 运行中' : '⏸️ 未运行' }}
        </span>
        <span>采集时间(UTC): {{ status.collect_hour_utc }}:00</span>
        <span>分析时间(UTC): {{ status.analyze_hour_utc }}:00</span>
        <span>报告: 周{{ status.report_day }} {{ status.report_hour_utc }}:00</span>
      </div>
      <div v-else class="loading">加载中...</div>
    </div>

    <!-- 定时任务列表 -->
    <div class="card">
      <div class="card-title">注册的定时任务</div>
      <table v-if="jobs.length">
        <thead><tr><th>ID</th><th>名称</th><th>下次执行</th><th>触发规则</th></tr></thead>
        <tbody>
          <tr v-for="j in jobs" :key="j.id">
            <td>{{ j.id }}</td>
            <td>{{ j.name }}</td>
            <td>{{ j.next_run_time ? new Date(j.next_run_time).toLocaleString('zh-CN') : '无' }}</td>
            <td><code>{{ j.trigger }}</code></td>
          </tr>
        </tbody>
      </table>
      <div v-else style="text-align:center; color:#aaa; padding:12px">暂无定时任务</div>
    </div>

    <!-- 手动触发 -->
    <div class="card">
      <div class="card-title">手动触发任务</div>
      <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:flex-end">
        <div class="form-group" style="margin-bottom:0; min-width:120px">
          <label>任务类型</label>
          <select v-model="trigger.job_type">
            <option value="collect">采集 collect</option>
            <option value="analyze">分析 analyze</option>
            <option value="report">报告 report</option>
          </select>
        </div>
        <div class="form-group" style="margin-bottom:0; min-width:140px">
          <label>主题</label>
          <select v-model.number="trigger.topic_id">
            <option :value="0">所有主题</option>
            <option v-for="t in topics" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
        <div v-if="trigger.job_type==='collect'" class="form-group" style="margin-bottom:0; min-width:80px">
          <label>最大采集数</label>
          <input type="number" v-model.number="trigger.max_items" min="1" max="200">
        </div>
        <div v-if="trigger.job_type==='analyze'" class="form-group" style="margin-bottom:0; min-width:80px">
          <label>最大分析数</label>
          <input type="number" v-model.number="trigger.max_analyze" min="1" max="100">
        </div>
        <button class="btn btn-success" @click="runJob" :disabled="running">
          {{ running ? '执行中...' : '🚀 执行' }}
        </button>
      </div>
    </div>

    <!-- 执行结果 -->
    <div v-if="result" class="card">
      <div class="card-title">执行结果</div>
      <div>
        <span class="badge" :class="result.status === 'success' ? 'badge-green' : 'badge-red'">
          {{ result.status }}
        </span>
        <span style="margin-left:8px">{{ result.job_type }} | 耗时 {{ result.duration_s?.toFixed(1) }}s</span>
      </div>
      <pre style="margin-top:8px; background:#f8f9fa; padding:12px; border-radius:6px; font-size:0.85em; overflow:auto; max-height:300px">{{ JSON.stringify(result, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const status = ref(null)
const jobs = ref([])
const topics = ref([])
const error = ref('')
const running = ref(false)
const result = ref(null)
const trigger = ref({ job_type: 'collect', topic_id: 0, max_items: 50, max_analyze: 20 })

async function loadData() {
  try {
    const [s, j, t] = await Promise.all([
      api.getSchedulerStatus(),
      api.listJobs(),
      api.listTopics(),
    ])
    status.value = s.data
    jobs.value = j.data
    topics.value = t.data
  } catch (e) {
    error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
  }
}

async function runJob() {
  running.value = true
  result.value = null
  error.value = ''
  try {
    const res = await api.triggerJob({
      job_type: trigger.value.job_type,
      topic_id: trigger.value.topic_id,
      max_items: trigger.value.max_items,
      max_analyze: trigger.value.max_analyze,
    })
    result.value = res.data
  } catch (e) {
    error.value = '执行失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    running.value = false
  }
}

onMounted(loadData)
</script>
