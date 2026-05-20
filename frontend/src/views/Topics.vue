<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h1 class="page-title" style="margin-bottom:0">🏷️ 主题管理</h1>
      <button class="btn btn-primary" @click="openCreate">+ 新建主题</button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="card">
      <div v-if="loading" class="loading">加载中...</div>
      <table v-else-if="topics.length">
        <thead>
          <tr><th>ID</th><th>名称</th><th>关键词</th><th>创建时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in topics" :key="t.id">
            <td>{{ t.id }}</td>
            <td><strong>{{ t.name }}</strong></td>
            <td>
              <span v-for="kw in t.keywords" :key="kw" class="badge badge-blue" style="margin-right:4px">{{ kw }}</span>
              <span v-if="!t.keywords?.length" style="color:#aaa">无</span>
            </td>
            <td>{{ formatTime(t.created_at) }}</td>
            <td>
              <button class="btn btn-warning btn-sm" @click="openEdit(t)" style="margin-right:4px">编辑</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else style="text-align:center; color:#aaa; padding: 20px">暂无主题，点击右上角创建</div>
    </div>

    <!-- 创建/编辑弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal=false">
      <div class="modal">
        <div class="modal-title">{{ editing ? '编辑主题' : '新建主题' }}</div>
        <div class="form-group">
          <label>主题名称 *</label>
          <input v-model="form.name" placeholder="例如：AI 技术动态">
        </div>
        <div class="form-group">
          <label>关键词（逗号分隔）</label>
          <input v-model="form.keywordsStr" placeholder="例如：LLM, GPT, AI Agent">
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showModal=false">取消</button>
          <button class="btn btn-primary" @click="save" :disabled="!form.name.trim()">
            {{ editing ? '更新' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const topics = ref([])
const loading = ref(true)
const error = ref('')
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: '', keywordsStr: '' })

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

async function loadTopics() {
  loading.value = true
  try {
    const res = await api.listTopics()
    topics.value = res.data
  } catch (e) {
    error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = { name: '', keywordsStr: '' }
  showModal.value = true
}

function openEdit(t) {
  editing.value = t.id
  form.value = { name: t.name, keywordsStr: (t.keywords || []).join(', ') }
  showModal.value = true
}

async function save() {
  const keywords = form.value.keywordsStr
    .split(',').map(s => s.trim()).filter(Boolean)
  try {
    if (editing.value) {
      await api.updateTopic(editing.value, { name: form.value.name, keywords })
    } else {
      await api.createTopic({ name: form.value.name, keywords })
    }
    showModal.value = false
    await loadTopics()
  } catch (e) {
    error.value = '操作失败: ' + (e.response?.data?.detail || e.message)
  }
}

onMounted(loadTopics)
</script>
