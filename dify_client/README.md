# Dify 内容分析工作流 — 配置与集成指南

## 概述

`dify_client` 模块负责将 Processor 输出的 `AnalysisInput` 发送给 Dify 内容分析工作流，获取 AI 生成的摘要、相关性评分、质量评分和标签。

数据流：

```text
Collector (RawItem) → Processor (AnalysisInput) → dify_client → Dify Workflow → AnalysisResult
```

## 第一步：在 Dify 中创建工作流应用

### 1.1 登录 Dify

打开浏览器访问 http://localhost（你的 Dify 地址），登录或完成初始化设置。

### 1.2 创建「工作流」应用

1. 点击左上角 **「创建应用」**
2. 选择 **「工作流」（Workflow）** 类型
3. 应用名称填：`内容分析工作流`（或 `Content Analysis Workflow`）
4. 点击创建

### 1.3 配置「开始」节点的输入变量

在工作流画布中，点击 **「开始」** 节点，添加以下 **6 个输入变量**：

| 变量名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `topic` | 文本 (String) | ✅ | 主题名，如「AI 工作流搭建」 |
| `title` | 文本 (String) | ✅ | 项目/文章标题 |
| `url` | 文本 (String) | ✅ | 原始 URL |
| `description` | 文本 (String) | ❌ | 项目描述 |
| `readme` | 段落 (Paragraph) | ✅ | 清洗后的 README/正文（可能很长） |
| `metadata` | 文本 (String) | ❌ | JSON 格式的元数据（stars, forks 等） |

> ⚠️ **变量名必须完全一致**（大小写敏感），否则 API 调用会报错。
> ⚠️ `readme` 建议用「段落」类型，因为内容可能较长（最多 8000 字符）。

### 1.4 添加 LLM 节点

1. 从「开始」节点拖出连线，添加一个 **「LLM」** 节点
2. 选择你配置好的模型（如 OpenAI GPT-4、Claude 等）
3. 在提示词中配置如下：

```
你是一个技术内容分析助手。请分析以下 GitHub 项目，并按要求输出结构化结果。

## 分析主题
{{topic}}

## 项目信息
- 标题：{{title}}
- URL：{{url}}
- 描述：{{description}}
- 元数据：{{metadata}}

## 项目 README
{{readme}}

## 输出要求
请以 JSON 格式输出以下字段：
{
  "summary": "用 2-3 句话中文描述这个项目的核心功能和亮点",
  "relevance_score": 0.0 到 1.0 的浮点数，表示与分析主题的相关度,
  "quality_score": 0.0 到 1.0 的浮点数，表示项目整体质量,
  "tags": ["标签1", "标签2", "标签3"]
}

评分标准：
- relevance_score: 1.0=高度相关, 0.7=较相关, 0.4=弱相关, 0.0=无关
- quality_score: 考虑文档完整性、代码活跃度、star 数、维护状态等
- tags: 3-5 个中文技术标签

只输出 JSON，不要输出其他内容。
```

### 1.5 添加「代码执行」节点（解析 JSON）

LLM 输出的是文本，需要解析为结构化字段：

1. 从 LLM 节点拖出连线，添加 **「代码执行」** 节点
2. 输入变量：`llm_output` ← 引用 LLM 节点的输出
3. 代码（Python）：

```python
import json
import re

def main(llm_output: str) -> dict:
    text = llm_output.strip()

    # 1. 剥离 <think>...</think> 思考过程（DeepSeek 等推理模型会输出）
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # 2. 提取 markdown 代码块中的 JSON
    match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    # 3. 如果还不是 JSON，尝试找第一个 { 到最后一个 }
    if not text.startswith('{'):
        brace_match = re.search(r'\{.*\}', text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {
            "summary": llm_output[:500],
            "relevance_score": 0.5,
            "quality_score": 0.5,
            "tags": "未分类"
        }

    tags = data.get("tags", [])
    if isinstance(tags, list):
        tags = ", ".join(str(t) for t in tags)

    return {
        "summary": str(data.get("summary", "")),
        "relevance_score": float(data.get("relevance_score", 0.5)),
        "quality_score": float(data.get("quality_score", 0.5)),
        "tags": tags
    }
```

> 💡 如果你使用的是 DeepSeek 等推理模型，LLM 输出会包含 `<think>...</think>` 标签，上面的代码会自动剥离它。

4. 输出变量定义：

| 变量名 | 类型 |
|--------|------|
| `summary` | String |
| `relevance_score` | Number |
| `quality_score` | Number |
| `tags` | String |

### 1.6 配置「结束」节点

1. 从代码执行节点拖出连线到 **「结束」** 节点
2. 在结束节点中配置输出变量，引用代码执行节点的输出：

| 输出变量名 | 引用 |
|-----------|------|
| `summary` | 代码执行节点.summary |
| `relevance_score` | 代码执行节点.relevance_score |
| `quality_score` | 代码执行节点.quality_score |
| `tags` | 代码执行节点.tags |

### 1.7 工作流最终结构

```text
[开始] → [LLM 内容分析] → [代码执行: JSON 解析] → [结束]
  ↑                                                    ↑
  输入: topic, title,                          输出: summary,
        url, description,                     relevance_score,
        readme, metadata                      quality_score, tags
```

### 1.8 测试工作流

1. 点击右上角的 **「运行」** 按钮
2. 填入测试数据：
   - topic: `AI 工作流搭建`
   - title: `langgenius/dify`
   - url: `https://github.com/langgenius/dify`
   - description: `Dify is an open-source LLM app development platform.`
   - readme: `（粘贴一段 README 内容）`
   - metadata: `{"stars": 50000, "forks": 7000, "programming_language": "Python"}`
3. 确认输出包含 summary, relevance_score, quality_score, tags

## 第二步：获取 API Key

1. 在 Dify 应用页面，点击左侧 **「API 访问」**（或 **「API Access」**）
2. 点击 **「API 密钥」** → **「创建密钥」**
3. 复制生成的 API Key（格式类似 `app-xxxxxxxxxxxxxxxx`）
4. 将其添加到项目的 `.env` 文件中：

```bash
DIFY_API_KEY=app-xxxxxxxxxxxxxxxx
DIFY_BASE_URL=http://localhost/v1
```

## 第三步：在代码中使用

### 基本用法

```python
from dify_client import DifyClient, DifyConfig

# 从环境变量加载配置
config = DifyConfig.from_env()
client = DifyClient(config)

# 健康检查
if client.health_check():
    print("Dify API 连接正常")

# 分析单条
result = client.analyze(analysis_input)
if result.succeeded:
    print(f"摘要: {result.summary}")
    print(f"相关性: {result.relevance_score}")
    print(f"质量分: {result.quality_score}")
    print(f"标签: {result.tags}")
else:
    print(f"分析失败: {result.error}")
```

### 完整 Pipeline 示例

```python
from collector import GitHubCollector, CollectorConfig
from processor import Processor, ProcessorConfig, ...
from dify_client import DifyClient, DifyConfig

# 1. 收集
collector = GitHubCollector(CollectorConfig.from_env())
raw_items = collector.collect(...)

# 2. 处理
processor = Processor(...)
analysis_inputs = processor.process_batch_to_analysis_inputs(raw_items)

# 3. Dify 分析
dify_client = DifyClient(DifyConfig.from_env())
results = dify_client.analyze_batch(analysis_inputs)

# 4. 输出结果
for inp, result in zip(analysis_inputs, results):
    if result.succeeded:
        print(f"[{inp.title}] {result.summary}")
        print(f"  相关性: {result.relevance_score:.2f}")
        print(f"  标签: {', '.join(result.tags)}")
```

## 常见问题

### Q: 需要先配置 LLM 模型吗？
**是的。** 在 Dify 中：设置 → 模型供应商 → 添加你的 OpenAI/Anthropic/其他模型的 API Key。工作流的 LLM 节点需要选择一个已配置的模型。

### Q: metadata 为什么是 JSON 字符串而不是对象？
Dify 工作流的输入变量只支持基础类型（String, Number, Boolean），不支持嵌套对象。所以我们将 metadata 序列化为 JSON 字符串传入，LLM 可以直接理解 JSON 文本。

### Q: 工作流超时怎么办？
默认超时 120 秒。如果 LLM 模型较慢，可以在 `.env` 中增加：
```bash
DIFY_TIMEOUT=300
```

### Q: 如何调整分析提示词？
直接在 Dify 工作流编辑器中修改 LLM 节点的提示词即可，不需要改代码。这就是使用 Dify 的好处——**提示词管理与代码解耦**。
