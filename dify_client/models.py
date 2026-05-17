"""Dify 分析结果模型。"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AnalysisResult:
    """Dify 工作流返回的内容分析结果。

    对应 STORAGE_INTERFACE_NOTES.md 中的 AnalysisResultRepository 字段。
    """

    source_id: Optional[int] = None  # 由 orchestration 层关联
    workflow_run_id: Optional[str] = None
    summary: str = ""
    relevance_score: float = 0.0
    quality_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    analyzed_at: Optional[datetime] = None

    # 额外字段，便于调试
    status: str = ""  # succeeded / failed / stopped
    elapsed_time: float = 0.0  # 工作流耗时（秒）
    total_tokens: int = 0
    error: Optional[str] = None

    @classmethod
    def from_dify_response(cls, response: Dict[str, Any]) -> "AnalysisResult":
        """从 Dify /workflows/run 的响应中解析结果。

        Dify Workflow API 响应结构：
        {
            "workflow_run_id": "...",
            "task_id": "...",
            "data": {
                "id": "...",
                "workflow_id": "...",
                "status": "succeeded",
                "outputs": {  <-- 这里是工作流的输出变量
                    "summary": "...",
                    "relevance_score": 0.85,
                    "quality_score": 0.9,
                    "tags": ["AI", "workflow"]
                },
                "elapsed_time": 12.5,
                "total_tokens": 1500,
                ...
            }
        }
        """
        data = response.get("data", {})
        outputs = data.get("outputs", {})

        # 解析 tags：可能是 list 或逗号分隔的字符串
        raw_tags = outputs.get("tags", [])
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = [str(t) for t in raw_tags]
        else:
            tags = []

        return cls(
            workflow_run_id=response.get("workflow_run_id"),
            summary=outputs.get("summary", ""),
            relevance_score=float(outputs.get("relevance_score", 0)),
            quality_score=float(outputs.get("quality_score", 0)),
            tags=tags,
            raw_response=response,
            analyzed_at=datetime.now(timezone.utc),
            status=data.get("status", "unknown"),
            elapsed_time=float(data.get("elapsed_time", 0)),
            total_tokens=int(data.get("total_tokens", 0)),
            error=data.get("error") if data.get("status") != "succeeded" else None,
        )

    @property
    def succeeded(self) -> bool:
        return self.status == "succeeded"
