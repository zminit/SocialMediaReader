<template>
  <div class="architecture-page">
    <header class="hero card">
      <div>
        <p class="eyebrow">Development Guide</p>
        <h1 class="page-title">🧭 项目架构与开发进度</h1>
        <p class="hero-desc">
          这个页面用于指导 SocialMediaReader 后续开发：集中展示当前模块边界、关键接口、数据流、API、里程碑和下一步开发重点。
        </p>
      </div>
      <div class="hero-meta">
        <div><strong>项目定位</strong><span>个人 AI 工作流调研系统</span></div>
        <div><strong>当前版本</strong><span>V0 / 开发期</span></div>
        <div><strong>主要链路</strong><span>GitHub → Processor → Dify → 展示</span></div>
      </div>
    </header>

    <section class="stats-grid progress-overview">
      <div class="card stat-card" v-for="item in progressStats" :key="item.label">
        <div class="stat-number" :style="{ color: item.color }">{{ item.value }}</div>
        <div class="stat-label">{{ item.label }}</div>
      </div>
    </section>

    <section class="card">
      <div class="section-heading">
        <div>
          <h2>项目模块结构图</h2>
          <p>按职责边界组织的当前模块全景。箭头表示主要依赖/调用方向。</p>
        </div>
      </div>

      <div class="module-map">
        <div class="map-lane external">
          <h3>外部系统</h3>
          <div class="node external-node">GitHub API</div>
          <div class="node external-node">Dify Workflow</div>
          <div class="node external-node">个人网站 / 用户</div>
        </div>

        <div class="map-lane core">
          <h3>核心业务链路</h3>
          <div class="flow-row">
            <div class="node done">Collector<br><small>外部采集</small></div>
            <span class="arrow">→</span>
            <div class="node done">Processor<br><small>清洗/去重/评分</small></div>
            <span class="arrow">→</span>
            <div class="node done">DifyClient<br><small>AI 工作流调用</small></div>
          </div>
          <div class="flow-row second">
            <div class="node done wide">Storage<br><small>SQLite 持久化 / Repository</small></div>
            <span class="arrow">↕</span>
            <div class="node done wide">Scheduler + Orchestrator<br><small>定时调度 / 流程编排</small></div>
          </div>
        </div>

        <div class="map-lane interface">
          <h3>访问与运维层</h3>
          <div class="flow-row">
            <div class="node done">FastAPI<br><small>REST 接口</small></div>
            <span class="arrow">→</span>
            <div class="node done">Vue Frontend<br><small>开发控制台</small></div>
            <span class="arrow">→</span>
            <div class="node todo">Website<br><small>个人网站展示</small></div>
          </div>
          <div class="flow-row second">
            <div class="node done wide">Logging<br><small>文件 + SQLite + 页面查看</small></div>
          </div>
        </div>
      </div>
    </section>

    <section class="grid two-col">
      <div class="card">
        <div class="section-heading compact">
          <h2>端到端数据流</h2>
        </div>
        <div class="data-flow">
          <div class="flow-step" v-for="(step, index) in dataFlow" :key="step.title">
            <div class="step-index">{{ index + 1 }}</div>
            <div>
              <h3>{{ step.title }}</h3>
              <p>{{ step.desc }}</p>
              <code>{{ step.artifact }}</code>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="section-heading compact">
          <h2>关键设计原则</h2>
        </div>
        <ul class="principles">
          <li v-for="principle in principles" :key="principle.title">
            <strong>{{ principle.title }}</strong>
            <span>{{ principle.desc }}</span>
          </li>
        </ul>
      </div>
    </section>

    <section class="card">
      <div class="section-heading">
        <div>
          <h2>模块功能、接口与状态</h2>
          <p>开发时优先遵守各模块职责边界，避免跨层写入或把编排逻辑下沉到基础模块。</p>
        </div>
      </div>

      <div class="module-grid">
        <article class="module-card" v-for="module in modules" :key="module.name">
          <div class="module-card-header">
            <span class="module-icon">{{ module.icon }}</span>
            <div>
              <h3>{{ module.name }}</h3>
              <span :class="['status-pill', module.statusClass]">{{ module.status }}</span>
            </div>
          </div>

          <p class="module-desc">{{ module.desc }}</p>

          <div class="mini-block">
            <strong>核心职责</strong>
            <ul>
              <li v-for="item in module.responsibilities" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div class="mini-block">
            <strong>核心接口/产物</strong>
            <div class="chip-list">
              <span class="chip" v-for="api in module.interfaces" :key="api">{{ api }}</span>
            </div>
          </div>

          <div class="mini-block">
            <strong>主要文件</strong>
            <code class="file-path">{{ module.path }}</code>
          </div>
        </article>
      </div>
    </section>

    <section class="grid two-col api-and-schema">
      <div class="card">
        <div class="section-heading compact">
          <h2>REST API 总览</h2>
        </div>
        <table class="compact-table">
          <thead>
            <tr>
              <th>领域</th>
              <th>接口</th>
              <th>用途</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in apiEndpoints" :key="item.endpoint">
              <td><span class="badge badge-blue">{{ item.domain }}</span></td>
              <td><code>{{ item.endpoint }}</code></td>
              <td>{{ item.desc }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="section-heading compact">
          <h2>数据库表与用途</h2>
        </div>
        <div class="schema-list">
          <div class="schema-item" v-for="table in databaseTables" :key="table.name">
            <code>{{ table.name }}</code>
            <span>{{ table.desc }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="card">
      <div class="section-heading">
        <div>
          <h2>开发里程碑与当前进度</h2>
          <p>用于判断下一阶段开发优先级。完成项代表代码层面已落地；待开发项需要继续细化需求与验收标准。</p>
        </div>
      </div>
      <div class="timeline">
        <div class="timeline-item" v-for="milestone in milestones" :key="milestone.id">
          <div :class="['timeline-dot', milestone.done ? 'done' : 'pending']"></div>
          <div class="timeline-content">
            <div class="timeline-title">
              <strong>{{ milestone.id }}</strong>
              <span>{{ milestone.title }}</span>
              <em :class="milestone.done ? 'done-text' : 'pending-text'">{{ milestone.status }}</em>
            </div>
            <p>{{ milestone.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="grid two-col">
      <div class="card">
        <div class="section-heading compact">
          <h2>当前已知风险 / 待确认点</h2>
        </div>
        <ul class="todo-list">
          <li v-for="risk in risks" :key="risk"><span>⚠️</span>{{ risk }}</li>
        </ul>
      </div>

      <div class="card next-actions">
        <div class="section-heading compact">
          <h2>建议下一步开发</h2>
        </div>
        <ol>
          <li v-for="action in nextActions" :key="action.title">
            <strong>{{ action.title }}</strong>
            <span>{{ action.desc }}</span>
          </li>
        </ol>
      </div>
    </section>
  </div>
</template>

<script setup>
const progressStats = [
  { label: '已完成核心模块', value: '7', color: '#27ae60' },
  { label: '待开发模块', value: '2', color: '#f39c12' },
  { label: '主要 API 分组', value: '7', color: '#0f3460' },
  { label: '核心数据表', value: '6+', color: '#8e44ad' },
]

const modules = [
  {
    icon: '📥',
    name: 'Collector',
    status: '已完成',
    statusClass: 'done',
    path: 'collector/',
    desc: '从外部信息源采集数据，并转换为标准 RawItem。当前重点支持 GitHub 仓库采集。',
    responsibilities: ['构造外部查询', '处理分页、限流、重试', '单批次 external_id 去重', '生成 RawItem'],
    interfaces: ['SourceQuery', 'RawItem', 'BaseCollector.collect()', 'GitHubCollector'],
  },
  {
    icon: '🧹',
    name: 'Processor',
    status: '已完成',
    statusClass: 'done',
    path: 'processor/',
    desc: '完成标准化、内容清洗、指纹计算、跨批次去重检查、质量评估，并输出 AnalysisInput。',
    responsibilities: ['Normalizer', 'ContentCleaner', 'FingerprintCalculator', 'DedupChecker', 'QualityFilter', 'DataTransformer'],
    interfaces: ['Processor.process_batch()', 'ProcessingResult', 'AnalysisInput', 'DedupRepository', 'TopicRepository'],
  },
  {
    icon: '🤖',
    name: 'DifyClient',
    status: '已完成',
    statusClass: 'done',
    path: 'dify_client/',
    desc: '封装 Dify Workflow API，将 AnalysisInput 发送到 AI 工作流并解析 AnalysisResult。',
    responsibilities: ['构建 /workflows/run 请求', '阻塞模式调用', '429/5xx 重试', '批量分析', '健康检查'],
    interfaces: ['DifyClient.analyze()', 'DifyClient.analyze_batch()', 'AnalysisResult', 'DifyConfig'],
  },
  {
    icon: '🗄️',
    name: 'Storage',
    status: '已完成',
    statusClass: 'done',
    path: 'storage/',
    desc: 'SQLite 持久化层，实现 Processor 所需只读接口，并为 Orchestrator 提供统一写入。',
    responsibilities: ['数据库初始化/迁移', '主题管理', '内容源 CRUD', '去重查询', '分析结果保存', '过滤/重复日志'],
    interfaces: ['Database', 'SQLiteTopicRepository', 'SQLiteSourceRepository', 'SQLiteAnalysisResultRepository'],
  },
  {
    icon: '⏱️',
    name: 'Scheduler + Orchestrator',
    status: '已完成',
    statusClass: 'done',
    path: 'scheduler/',
    desc: 'APScheduler 定时调度与业务流程编排，串联采集、处理、分析、存储。',
    responsibilities: ['定时任务注册', '手动触发任务', '采集流程编排', '分析流程编排', 'Job 状态记录'],
    interfaces: ['Orchestrator.run_collect()', 'Orchestrator.run_analyze()', 'Scheduler.trigger_job()', 'Scheduler.get_jobs()'],
  },
  {
    icon: '🔌',
    name: 'API',
    status: '已完成',
    statusClass: 'done',
    path: 'api/',
    desc: 'FastAPI REST 层，提供主题、内容、分析结果、任务、统计和日志查看接口。',
    responsibilities: ['应用生命周期管理', '依赖注入', 'REST Router', 'CORS', '请求日志中间件'],
    interfaces: ['/api/topics', '/api/sources', '/api/analysis', '/api/jobs', '/api/stats', '/api/logs'],
  },
  {
    icon: '🖥️',
    name: 'Frontend Console',
    status: '已完成/持续增强',
    statusClass: 'progress',
    path: 'frontend/src/views/',
    desc: 'Vue 开发控制台，用于查看仪表盘、主题、采集内容、分析结果、调度任务、系统日志和架构进度。',
    responsibilities: ['业务数据查看', '任务手动触发', '日志可视化', '开发指导页面'],
    interfaces: ['Dashboard.vue', 'Topics.vue', 'Sources.vue', 'Analysis.vue', 'Jobs.vue', 'Logs.vue'],
  },
  {
    icon: '📋',
    name: 'Logging',
    status: '已完成',
    statusClass: 'done',
    path: 'logging_config/',
    desc: '统一日志系统，输出到控制台、文件和 SQLite，并在前端提供查询页面。',
    responsibilities: ['统一格式', '文件轮转', '错误日志', '请求日志', '日志查询统计'],
    interfaces: ['setup_logging()', 'RequestLoggingMiddleware', 'LogQueryService', '/api/logs'],
  },
  {
    icon: '🌐',
    name: 'Website',
    status: '待开发',
    statusClass: 'todo',
    path: '待定',
    desc: '面向最终个人网站的内容展示层，展示精选结果、主题页面、周报归档等。',
    responsibilities: ['公开展示', '周报归档', '主题导航', 'SEO/静态化策略'],
    interfaces: ['待定：内容发布 API', '待定：静态页面生成', '待定：RSS/分享'],
  },
]

const dataFlow = [
  { title: '主题配置', desc: '用户在前端/API 创建 Topic，配置关键词和采集范围。', artifact: 'Topic / SourceQuery' },
  { title: '外部采集', desc: 'Collector 根据关键词调用 GitHub API，处理分页、限流和单批去重。', artifact: 'RawItem[]' },
  { title: '处理过滤', desc: 'Processor 标准化 URL/metadata，清洗内容，计算指纹，查询 Storage 去重并做质量评估。', artifact: 'ProcessingResult[]' },
  { title: '写入来源', desc: 'Orchestrator 根据处理结果写入 sources、duplicate_records 或 filtered_records。', artifact: 'sources / duplicate_records / filtered_records' },
  { title: 'AI 分析', desc: 'DifyClient 将通过项发送到 Dify Workflow，得到摘要、相关性、质量分、标签等。', artifact: 'AnalysisResult' },
  { title: '结果展示', desc: 'API 将存储数据提供给 Vue 控制台；后续 Website 模块面向个人网站展示。', artifact: 'Dashboard / Analysis / Website' },
]

const principles = [
  { title: 'Collector 不做业务判断', desc: '只负责采集、限流、重试和 RawItem 转换，不做跨批次去重和 AI 分析。' },
  { title: 'Processor 只读 Storage', desc: 'Processor 可通过接口查询去重和主题名，但不直接写数据库。' },
  { title: 'Orchestrator 统一写入', desc: '所有流程写入统一由编排层控制，保证状态流转清晰。' },
  { title: 'API 只做访问层', desc: 'Router 不承载核心业务逻辑，通过依赖注入调用 Repository / Scheduler / Orchestrator。' },
  { title: '日志可观测', desc: '每个关键流程应记录结构化日志，便于前端日志页排查问题。' },
]

const apiEndpoints = [
  { domain: 'Health', endpoint: 'GET /health', desc: '系统健康检查' },
  { domain: 'Topics', endpoint: 'GET/POST /api/topics', desc: '主题列表与创建' },
  { domain: 'Topics', endpoint: 'GET/PUT /api/topics/{id}', desc: '主题详情与更新' },
  { domain: 'Sources', endpoint: 'GET /api/sources', desc: '内容源列表，支持 topic_id/status 过滤' },
  { domain: 'Sources', endpoint: 'GET /api/sources/{id}', desc: '内容源详情' },
  { domain: 'Analysis', endpoint: 'GET /api/analysis', desc: '分析结果列表' },
  { domain: 'Analysis', endpoint: 'GET /api/analysis/source/{id}', desc: '按 source 查询分析结果' },
  { domain: 'Jobs', endpoint: 'GET /api/jobs/status', desc: '调度器状态' },
  { domain: 'Jobs', endpoint: 'GET /api/jobs', desc: '定时任务列表' },
  { domain: 'Jobs', endpoint: 'POST /api/jobs/trigger', desc: '手动触发 collect/analyze' },
  { domain: 'Stats', endpoint: 'GET /api/stats', desc: '系统统计信息' },
  { domain: 'Logs', endpoint: 'GET /api/logs', desc: '日志分页查询/过滤' },
  { domain: 'Logs', endpoint: 'GET /api/logs/stats', desc: '日志统计' },
  { domain: 'Logs', endpoint: 'DELETE /api/logs', desc: '清理日志' },
]

const databaseTables = [
  { name: 'topics', desc: '主题管理：name、keywords 等' },
  { name: 'sources', desc: '通过处理流程保留下来的内容源' },
  { name: 'duplicate_records', desc: '被判定重复的 RawItem 记录' },
  { name: 'filtered_records', desc: '被质量过滤/硬过滤的记录' },
  { name: 'analysis_results', desc: 'Dify 工作流返回的分析结果' },
  { name: 'schema_version', desc: '数据库 schema 版本跟踪' },
  { name: 'logs', desc: '日志模块 SQLite 表，支持前端查询' },
]

const milestones = [
  { id: 'M1', title: 'GitHub 采集可用', status: '完成', done: true, desc: 'Collector + GitHubCollector 已具备采集、限流、分页和 RawItem 转换能力。' },
  { id: 'M2', title: 'Processor 清洗、去重、质量评估', status: '完成', done: true, desc: '已形成 RawItem → AnalysisInput 的标准处理链路。' },
  { id: 'M2.5', title: 'DifyClient 工作流调用', status: '完成', done: true, desc: '已封装 Dify Workflow API 调用和结果解析。' },
  { id: 'M3', title: 'Storage 模块', status: '完成', done: true, desc: 'SQLite 持久化、Repository 和基础迁移已落地。' },
  { id: 'M4', title: 'Scheduler + Orchestrator', status: '完成', done: true, desc: '定时调度与流程编排已具备基础能力。' },
  { id: 'M5', title: 'Dify 内容分析工作流', status: '待完善', done: false, desc: '需要进一步固化 Workflow 输入/输出字段、失败重试策略和质量评估提示词。' },
  { id: 'M6', title: 'API + 前端控制台', status: '完成/增强中', done: true, desc: 'API、Dashboard、日志页、架构页等已集成，后续按开发需要继续扩展。' },
  { id: 'M7', title: '周报生成与 Website 展示', status: '待开发', done: false, desc: '需要设计周报聚合逻辑、发布模型和个人网站展示方式。' },
]

const risks = [
  'Processor 初始化曾出现 DataTransformer 配置参数缺失警告，需要在后续流程测试中重点验证。',
  'Dify Workflow 的实际输出字段需要与 AnalysisResult 解析逻辑保持严格一致。',
  'Docker/Dify 目录存在权限敏感文件，使用 uvicorn --reload 时可能触发 watch 权限问题。',
  'Website 模块尚未确定是静态生成、SSR，还是由现有 API 动态驱动。',
]

const nextActions = [
  { title: '补齐 Dify Workflow 验收', desc: '定义固定输入/输出 schema，准备失败样例、超时样例和高质量样例。' },
  { title: '完善端到端测试', desc: '从 Topic → Collect → Process → Analyze → Storage → Frontend 全链路验证。' },
  { title: '设计周报生成模型', desc: '明确周报周期、排序规则、内容结构、人工编辑入口和发布格式。' },
  { title: '规划 Website 模块', desc: '确定展示页面、路由结构、数据来源和部署方式。' },
]
</script>

<style scoped>
.architecture-page { display: flex; flex-direction: column; gap: 16px; }

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 24px;
  align-items: center;
  background: linear-gradient(135deg, #ffffff 0%, #eef5ff 100%);
}
.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.75em;
  color: #0f3460;
  font-weight: 700;
  margin-bottom: 8px;
}
.hero .page-title { margin-bottom: 10px; }
.hero-desc { color: #555; line-height: 1.7; max-width: 820px; }
.hero-meta {
  display: grid;
  gap: 10px;
}
.hero-meta div {
  background: rgba(255,255,255,0.75);
  border: 1px solid #dce7f5;
  border-radius: 10px;
  padding: 12px;
}
.hero-meta strong { display: block; color: #1a1a2e; margin-bottom: 4px; }
.hero-meta span { color: #666; font-size: 0.9em; }

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.section-heading h2 {
  font-size: 1.2em;
  color: #1a1a2e;
  margin-bottom: 6px;
}
.section-heading p { color: #777; font-size: 0.92em; }
.section-heading.compact { margin-bottom: 12px; }

.grid.two-col {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.module-map {
  display: grid;
  gap: 14px;
}
.map-lane {
  border: 1px solid #e8edf4;
  border-radius: 12px;
  padding: 16px;
  background: #fbfcff;
}
.map-lane h3 {
  font-size: 0.95em;
  color: #555;
  margin-bottom: 12px;
}
.flow-row {
  display: flex;
  align-items: stretch;
  gap: 10px;
  flex-wrap: wrap;
}
.flow-row.second { margin-top: 12px; }
.node {
  min-width: 150px;
  padding: 14px 16px;
  border-radius: 12px;
  font-weight: 700;
  line-height: 1.4;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.node small { font-weight: 500; color: rgba(0,0,0,0.55); }
.node.done { background: #eaf8ef; border: 1px solid #bce7c9; color: #155724; }
.node.todo { background: #fff7e6; border: 1px solid #ffe0a3; color: #856404; }
.external-node { background: #f1f4ff; border: 1px solid #d5dcff; color: #283593; display: inline-block; margin-right: 8px; margin-bottom: 8px; }
.node.wide { min-width: 260px; }
.arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #888;
  font-size: 1.4em;
  min-width: 24px;
}

.data-flow { display: grid; gap: 12px; }
.flow-step {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  background: #f8f9fa;
  border: 1px solid #eee;
}
.step-index {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #0f3460;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}
.flow-step h3 { font-size: 1em; margin-bottom: 4px; color: #1a1a2e; }
.flow-step p { color: #666; font-size: 0.9em; margin-bottom: 6px; line-height: 1.5; }
code {
  background: #f3f4f6;
  color: #0f3460;
  border-radius: 5px;
  padding: 2px 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.86em;
}

.principles { list-style: none; display: grid; gap: 12px; }
.principles li {
  padding: 12px;
  border-radius: 10px;
  background: #fbfcff;
  border-left: 4px solid #0f3460;
}
.principles strong { display: block; color: #1a1a2e; margin-bottom: 4px; }
.principles span { color: #666; font-size: 0.92em; line-height: 1.5; }

.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 14px;
}
.module-card {
  border: 1px solid #e8edf4;
  border-radius: 12px;
  padding: 16px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.module-card-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.module-icon { font-size: 1.8em; }
.module-card h3 { margin-bottom: 6px; color: #1a1a2e; }
.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.76em;
  font-weight: 700;
}
.status-pill.done { background: #d4edda; color: #155724; }
.status-pill.progress { background: #cce5ff; color: #004085; }
.status-pill.todo { background: #fff3cd; color: #856404; }
.module-desc { color: #666; line-height: 1.55; font-size: 0.92em; margin-bottom: 12px; }
.mini-block { margin-top: 12px; }
.mini-block strong { color: #555; display: block; margin-bottom: 6px; }
.mini-block ul { padding-left: 18px; color: #666; font-size: 0.9em; line-height: 1.6; }
.chip-list { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  background: #f1f5f9;
  color: #334155;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 0.8em;
}
.file-path { display: inline-block; }

.compact-table { font-size: 0.88em; }
.compact-table th, .compact-table td { padding: 8px; vertical-align: top; }
.compact-table code { white-space: nowrap; }

.schema-list { display: grid; gap: 10px; }
.schema-item {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr);
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #f8f9fa;
  align-items: center;
}
.schema-item span { color: #666; font-size: 0.9em; }

.timeline { position: relative; display: grid; gap: 14px; }
.timeline-item {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 12px;
}
.timeline-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  margin-top: 4px;
}
.timeline-dot.done { background: #27ae60; box-shadow: 0 0 0 4px #d4edda; }
.timeline-dot.pending { background: #f39c12; box-shadow: 0 0 0 4px #fff3cd; }
.timeline-content {
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}
.timeline-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}
.timeline-title strong { color: #0f3460; }
.timeline-title span { font-weight: 700; color: #1a1a2e; }
.timeline-title em { font-style: normal; font-size: 0.8em; margin-left: auto; }
.done-text { color: #27ae60; }
.pending-text { color: #f39c12; }
.timeline-content p { color: #666; line-height: 1.5; font-size: 0.9em; }

.todo-list { list-style: none; display: grid; gap: 10px; }
.todo-list li {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  color: #666;
  line-height: 1.55;
  padding: 10px;
  border-radius: 8px;
  background: #fffaf0;
}
.next-actions ol { padding-left: 20px; display: grid; gap: 12px; }
.next-actions li { color: #666; line-height: 1.5; }
.next-actions strong { display: block; color: #1a1a2e; }

@media (max-width: 1100px) {
  .hero, .grid.two-col { grid-template-columns: 1fr; }
  .schema-item { grid-template-columns: 1fr; }
}
</style>