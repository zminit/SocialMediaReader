# Collector 模块手动测试指南

本文档说明如何手动检查 Collector 模块的运行情况。

## 运行示例脚本

### 1. 准备工作

确保已配置 `.env` 文件中的 `GITHUB_TOKEN`：

```bash
# 检查配置
cat .env | grep GITHUB_TOKEN
```

### 2. 运行示例脚本

使用以下命令运行完整的示例脚本：

```bash
PYTHONPATH=. .venv/bin/python examples/basic_usage.py
```

### 3. 示例脚本包含的测试场景

脚本会依次运行 4 个示例：

#### 示例 1: 基础搜索
- 搜索关键词：`machine learning`, `deep learning`
- 编程语言：Python
- 最小 Stars：100
- 排序方式：按 Stars 排序
- 采集数量：10 条

**输出示例：**
```
找到: transformers (huggingface)
  URL: https://github.com/huggingface/transformers
  Stars: 160571
  Activity Score: 1.0
  Language: Python
```

#### 示例 2: Best Match 搜索
- 搜索关键词：`rust web framework`
- 编程语言：Rust
- 排序方式：相关性排序（best_match）
- 采集数量：5 条

**输出示例：**
```
1. Rocket (rwf2)
   Stars: 25737, Keyword: rust web framework
```

#### 示例 3: 带 Topics 过滤
- 搜索关键词：`web framework`
- 编程语言：TypeScript
- Topics 过滤：`react`, `nextjs`
- 排序方式：按更新时间排序
- 采集数量：5 条

**输出示例：**
```
webiny-js
  Topics: ai-assisted-development, aws, aws-lambda, cms, graphql
  Updated: 2026-05-13T13:47:26+00:00
```

#### 示例 4: Rate Limit 状态监控
- 展示如何监控 GitHub API 配额使用情况
- 显示采集前后的 Rate Limit 状态

**输出示例：**
```
初始 Rate Limit 状态:
  Remaining: 4960/5000
  Reset at: 2026-05-13T22:16:02
  Buffer: 100
```

## 查看输出结果

### 1. 控制台输出

脚本运行时会在控制台实时显示：
- Rate Limit 状态
- 采集进度（当前关键词、页码）
- 每个采集到的项目信息
- 日志信息（INFO、WARNING 级别）

### 2. JSON 结果文件

脚本会生成 `results_basic.json` 文件，包含完整的采集结果：

```bash
# 查看结果文件
cat results_basic.json | jq '.[0]'  # 查看第一条结果（需要安装 jq）

# 或直接查看
cat results_basic.json
```

**结果文件结构：**
```json
{
  "topic_id": 1,
  "source_type": "github",
  "source_subtype": "github_repo",
  "external_id": "github:huggingface/transformers",
  "url": "https://github.com/huggingface/transformers",
  "title": "transformers",
  "author": "huggingface",
  "description": "...",
  "published_at": "2018-10-29T13:56:00+00:00",
  "collected_at": "2026-05-13T13:58:34.613415+00:00",
  "raw_text": "...",
  "metadata": {
    "stars": 160571,
    "forks": 33195,
    "language": "Python",
    "topics": [...],
    "activity_score": 1.0,
    ...
  }
}
```

## 运行测试套件

如果想运行完整的测试套件：

```bash
# 运行所有测试
PYTHONPATH=. .venv/bin/pytest tests/ -v

# 只运行单元测试
PYTHONPATH=. .venv/bin/pytest tests/test_collector.py -v

# 只运行集成测试（需要 GITHUB_TOKEN）
PYTHONPATH=. .venv/bin/pytest tests/test_integration.py -v
```

## 自定义测试

### 使用 Python 交互式环境

```bash
PYTHONPATH=. .venv/bin/python
```

然后执行：

```python
from dotenv import load_dotenv
from collector import GitHubCollector, SourceQuery, CollectorConfig

# 加载环境变量
load_dotenv()

# 创建 collector
config = CollectorConfig.from_env()
collector = GitHubCollector(config)

# 查看 Rate Limit 状态
print(collector.get_rate_limit_status())

# 创建自定义查询
query = SourceQuery(
    topic_id=1,
    keywords=["your-keyword"],
    source_type="github",
    max_items=5,
    programming_language="Python"  # 可选
)

# 执行采集
for item in collector.collect(query):
    print(f"{item.title} - {item.url}")
    print(f"Stars: {item.metadata['stars']}")
    print("-" * 50)
```

## 关键指标说明

### Rate Limit 状态
- **remaining**: 剩余可用请求数
- **limit**: 总请求限额（未认证：10/小时，已认证：5000/小时）
- **reset_at**: 配额重置时间
- **buffer**: 安全缓冲区（默认 100）

### Activity Score
- 范围：0.0 - 1.0
- 综合考虑：Stars、Forks、最近更新时间、Open Issues
- 越接近 1.0 表示项目越活跃

### 采集性能
- 每次搜索请求：1 个 API 调用
- 每个项目详情：1 个 API 调用
- Rate Limit 保护：接近限额时自动等待

## 常见问题

### 1. ModuleNotFoundError: No module named 'collector'

确保使用 `PYTHONPATH=.` 前缀：
```bash
PYTHONPATH=. .venv/bin/python examples/basic_usage.py
```

### 2. Rate Limit 警告

这是正常的保护机制，脚本会自动等待配额重置。如果想避免等待：
- 减少 `max_items` 数量
- 增加 `page_size` 以减少请求次数

### 3. 采集速度慢

由于 GitHub API 限制和 Rate Limit 保护机制，采集速度会受限。这是正常现象。

## 最新测试结果

**测试时间**: 2026-05-13 22:03:20

**测试结果**:
- ✅ 示例 1: 成功采集 10 条机器学习相关项目
- ✅ 示例 2: 成功采集 5 条 Rust web 框架项目
- ✅ 示例 3: 成功采集 5 条带 Topics 过滤的项目
- ✅ 示例 4: Rate Limit 监控正常工作

**Rate Limit 使用情况**:
- 初始: 4980/5000
- 结束: 4957/5000
- 消耗: 23 个请求

**生成文件**:
- `results_basic.json`: 10 条完整的采集结果（1750 行 JSON）
