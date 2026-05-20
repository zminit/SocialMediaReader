<template>
  <div class="app-layout">
    <nav class="sidebar">
      <div class="logo">📡 SMReader</div>
      <router-link to="/" class="nav-item">📊 仪表盘</router-link>
      <router-link to="/topics" class="nav-item">🏷️ 主题管理</router-link>
      <router-link to="/sources" class="nav-item">📄 采集内容</router-link>
      <router-link to="/analysis" class="nav-item">🔍 分析结果</router-link>
      <router-link to="/jobs" class="nav-item">⚙️ 任务调度</router-link>
      <router-link to="/logs" class="nav-item">📋 系统日志</router-link>
      <router-link to="/architecture" class="nav-item">🧭 开发指南</router-link>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #333; }

.app-layout { display: flex; min-height: 100vh; }

.sidebar {
  width: 220px; background: #1a1a2e; color: #fff; padding: 20px 0;
  display: flex; flex-direction: column; position: fixed; top: 0; bottom: 0;
}
.logo { font-size: 1.4em; font-weight: bold; padding: 0 20px 20px; border-bottom: 1px solid #333; margin-bottom: 10px; }
.nav-item {
  display: block; padding: 12px 20px; color: #aaa; text-decoration: none;
  transition: all 0.2s; font-size: 0.95em;
}
.nav-item:hover { background: #16213e; color: #fff; }
.nav-item.router-link-active, .nav-item.router-link-exact-active { background: #0f3460; color: #fff; border-left: 3px solid #e94560; }

.main-content { margin-left: 220px; flex: 1; padding: 24px; }

.page-title { font-size: 1.5em; margin-bottom: 20px; color: #1a1a2e; }

.card {
  background: #fff; border-radius: 8px; padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px;
}
.card-title { font-size: 1.1em; font-weight: 600; margin-bottom: 12px; color: #555; }

.btn {
  display: inline-block; padding: 8px 16px; border: none; border-radius: 6px;
  cursor: pointer; font-size: 0.9em; transition: opacity 0.2s;
}
.btn:hover { opacity: 0.85; }
.btn-primary { background: #0f3460; color: #fff; }
.btn-success { background: #27ae60; color: #fff; }
.btn-danger { background: #e74c3c; color: #fff; }
.btn-warning { background: #f39c12; color: #fff; }
.btn-sm { padding: 4px 10px; font-size: 0.8em; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }
.stat-card { text-align: center; }
.stat-number { font-size: 2em; font-weight: bold; color: #0f3460; }
.stat-label { color: #888; font-size: 0.9em; margin-top: 4px; }

table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #f8f9fa; font-weight: 600; color: #555; font-size: 0.9em; }
tr:hover { background: #f8f9fa; }

.badge {
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 0.8em; font-weight: 500;
}
.badge-green { background: #d4edda; color: #155724; }
.badge-yellow { background: #fff3cd; color: #856404; }
.badge-red { background: #f8d7da; color: #721c24; }
.badge-blue { background: #cce5ff; color: #004085; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 0.9em; color: #555; margin-bottom: 4px; }
.form-group input, .form-group select, .form-group textarea {
  width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9em;
}

.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal { background: #fff; border-radius: 10px; padding: 24px; width: 480px; max-width: 90vw; }
.modal-title { font-size: 1.2em; margin-bottom: 16px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }

.loading { text-align: center; padding: 40px; color: #888; }
.error { background: #f8d7da; color: #721c24; padding: 12px; border-radius: 6px; margin-bottom: 16px; }
</style>
