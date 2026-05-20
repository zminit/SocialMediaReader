<template>
  <div>
    <h1 class="page-title">📄 采集内容</h1>

    <div v-if="error" class="error">{{ error }}</div>

    <!-- 过滤 -->
    <div class="card" style="display:flex; gap:12px; align-items:flex-end; flex-wrap:wrap">
      <div class="form-group" style="margin-bottom:0; min-width:140px">
        <label>主题</label>
        <select v-model="filter.topic_id" @change="load">
          <option :value="null">全部</option>
          <option v-for="t in topics" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom:0; min-width:140px">
        <label>状态</label>
        <select v-model="filter.status" @change="load">
          <option :value="null">全部</option>
          <option value="pending_analysis">待分析</option>
          <option value="analyzed">已分析</option>
          <option value="analysis_failed">分析失败</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom:0; min-width:80px">
        <label>数量</label>
        <select v-model.number="filter.limit" @change="load">
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>
    </div>

    <div class="card">
      <div v-if="loading" class="loading">加载中...</div>
      <table v-else-if="sources.length">
        <thead>
          <tr><th>ID</th><th>标题</th><th>来源</th><th>状态</th><th>采集时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="s in sources" :key="s.id">
            <td>{{ s.id }}</td>
            <td style="max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">
              <a v-if="s.url" :href="s.url" target="_blank" style="color:#0f3460">{{ s.title || s.url }}</a>
              <span v-else>{{ s.title || '-' }}</span>
            </td>
            <td><span class="badge badge-blue">{{ s.platform || s.source_type || '-' }}</span></td>
            <td>
              <span class="badge" :class="statusBadge(s.status)">{{ s.status }}</span>
            </td>
            <td>{{ formatTime(s.collected_at || s.created_at) }}</td>
            <td>
              <button class="btn btn-sm btn-primary" @click="showDetail(s)">详情</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else style="text-align:center; color:#aaa; padding:20px">暂无数据</div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detail" class="modal-overlay" @click.self="detail=null">
      <div class="modal" style="max-height:80vh; overflow-y:auto">
        <div class="modal-title">内容详情 #{{ detail.id }}</div>
        <div v-for="(v, k) in detail" :key="k" style="margin-bottom:8px">
          <strong style="color:#555">{{ k }}:</strong>
          <span v-if="typeof v === 'string' && v.length > 200" style="white-space:pre-wrap; font-size:0.9em">{{ v }}</span>
          <span v-else>{{ v }}</span>
        </div>
        <div class="modal-actions">
          <button class="btn btn-primary" @click="detail=null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const sources = ref([])
const topics = ref([])
const loading = ref(true)
const error = ref('')
const detail = ref(null)
const filter = ref({ topic_id: null, status: null, limit: 50 })

function statusBadge(s) {
  if (s === 'analyzed') return 'badge-green'
  if (s === 'pending_analysis') return 'badge-yellow'
  if (s === 'analysis_failed') return 'badge-red'
  return 'badge-blue'
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

async function load() {
  loading.value = true
  try {
    const params = { limit: filter.value.limit }
    if (filter.value.topic_id) params.topic_id = filter.value.topic_id
    if (filter.value.status) params.status = filter.value.status
    const res = await api.listSources(params)
    sources.value = res.data
  } catch (e) {
    error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function showDetail(s) {
  try {
    const res = await api.getSource(s.id)
    detail.value = res.data
  } catch {
    detail.value = s
  }
}

onMounted(async () => {
  try { topics.value = (await api.listTopics()).data } catch {}
  await load()
})
</script>
