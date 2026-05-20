<template>
  <div>
    <h1 class="page-title">🔍 分析结果</h1>

    <div v-if="error" class="error">{{ error }}</div>

    <!-- 过滤 -->
    <div class="card" style="display:flex; gap:12px; align-items:flex-end; flex-wrap:wrap">
      <div class="form-group" style="margin-bottom:0; min-width:160px">
        <label>选择主题 *</label>
        <select v-model.number="filter.topic_id" @change="load">
          <option :value="0" disabled>请选择主题</option>
          <option v-for="t in topics" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom:0; min-width:120px">
        <label>最低相关性</label>
        <input type="number" v-model.number="filter.min_relevance" min="0" max="1" step="0.1" @change="load">
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
      <div v-if="!filter.topic_id" style="text-align:center; color:#aaa; padding:20px">请先选择一个主题</div>
      <div v-else-if="loading" class="loading">加载中...</div>
      <table v-else-if="results.length">
        <thead>
          <tr><th>Source ID</th><th>相关性</th><th>摘要</th><th>关键词</th><th>分析时间</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in results" :key="r.id || r.source_id">
            <td>{{ r.source_id }}</td>
            <td>
              <span class="badge" :class="relevanceBadge(r.relevance_score)">
                {{ (r.relevance_score * 100).toFixed(0) }}%
              </span>
            </td>
            <td style="max-width:400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">
              {{ r.summary || '-' }}
            </td>
            <td>
              <span v-for="kw in (r.keywords || [])" :key="kw" class="badge badge-blue" style="margin-right:4px">{{ kw }}</span>
            </td>
            <td>{{ formatTime(r.analyzed_at || r.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else style="text-align:center; color:#aaa; padding:20px">暂无分析结果</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const topics = ref([])
const results = ref([])
const loading = ref(false)
const error = ref('')
const filter = ref({ topic_id: 0, min_relevance: 0, limit: 50 })

function relevanceBadge(score) {
  if (score >= 0.7) return 'badge-green'
  if (score >= 0.4) return 'badge-yellow'
  return 'badge-red'
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

async function load() {
  if (!filter.value.topic_id) return
  loading.value = true
  try {
    const res = await api.listAnalysis({
      topic_id: filter.value.topic_id,
      min_relevance: filter.value.min_relevance,
      limit: filter.value.limit,
    })
    results.value = res.data
  } catch (e) {
    error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    topics.value = (await api.listTopics()).data
    if (topics.value.length) {
      filter.value.topic_id = topics.value[0].id
      await load()
    }
  } catch {}
})
</script>
