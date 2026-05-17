"""Dify Workflow API 客户端。"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from processor.models import AnalysisInput

from .config import DifyConfig
from .models import AnalysisResult

logger = logging.getLogger(__name__)


class DifyClient:
    """调用 Dify Workflow 的客户端。

    使用 Dify 的 /workflows/run API（阻塞模式）将 Processor
    输出的 AnalysisInput 发送给 Dify 内容分析工作流。

    Usage:
        config = DifyConfig.from_env()
        client = DifyClient(config)
        result = client.analyze(analysis_input)
        if result.succeeded:
            print(result.summary, result.tags)
    """

    def __init__(self, config: DifyConfig):
        config.validate()
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }
        )

    def analyze(
        self,
        analysis_input: AnalysisInput,
        user: str = "system",
    ) -> AnalysisResult:
        """将单个 AnalysisInput 发送给 Dify 工作流进行分析。

        Args:
            analysis_input: Processor 输出的分析输入
            user: Dify API 要求的用户标识

        Returns:
            AnalysisResult: 分析结果
        """
        payload = self._build_payload(analysis_input, user)
        response = self._call_workflow(payload)
        result = AnalysisResult.from_dify_response(response)

        if result.succeeded:
            logger.info(
                "Dify analysis succeeded: %s (%.1fs, %d tokens)",
                analysis_input.title[:50],
                result.elapsed_time,
                result.total_tokens,
            )
        else:
            logger.warning(
                "Dify analysis failed: %s - %s",
                analysis_input.title[:50],
                result.error,
            )

        return result

    def analyze_batch(
        self,
        inputs: List[AnalysisInput],
        user: str = "system",
        delay: float = 1.0,
    ) -> List[AnalysisResult]:
        """批量分析，逐条调用工作流。

        Args:
            inputs: AnalysisInput 列表
            user: 用户标识
            delay: 每次调用间隔（秒），避免过快

        Returns:
            与 inputs 等长的 AnalysisResult 列表
        """
        results = []
        for i, inp in enumerate(inputs):
            logger.info("Analyzing %d/%d: %s", i + 1, len(inputs), inp.title[:50])
            result = self.analyze(inp, user=user)
            results.append(result)
            if i < len(inputs) - 1 and delay > 0:
                time.sleep(delay)

        succeeded = sum(1 for r in results if r.succeeded)
        logger.info(
            "Batch analysis complete: %d/%d succeeded", succeeded, len(results)
        )
        return results

    def _build_payload(
        self, analysis_input: AnalysisInput, user: str
    ) -> Dict[str, Any]:
        """构建 Dify /workflows/run 请求体。

        Dify Workflow API 要求的请求体格式：
        {
            "inputs": {
                "variable_name": "value",
                ...
            },
            "response_mode": "blocking",
            "user": "user_id"
        }

        inputs 中的 key 必须与 Dify 工作流「开始」节点定义的
        输入变量名完全一致。
        """
        dify_payload = analysis_input.to_dify_payload()

        # 将 metadata dict 序列化为 JSON 字符串，
        # 因为 Dify 工作流输入变量不支持嵌套对象
        metadata = dify_payload.pop("metadata", {})

        inputs = {
            "topic": dify_payload.get("topic", ""),
            "title": dify_payload.get("title", ""),
            "url": dify_payload.get("url", ""),
            "description": dify_payload.get("description") or "",
            "readme": dify_payload.get("readme", ""),
            "metadata": json.dumps(metadata, ensure_ascii=False, default=str),
        }

        return {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user,
        }

    def _call_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用 Dify /workflows/run API，含重试逻辑。"""
        url = f"{self.config.base_url.rstrip('/')}/workflows/run"
        last_error: Optional[Exception] = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                resp = self.session.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout,
                )

                if resp.status_code == 200:
                    return resp.json()

                # Dify 返回错误
                error_body = resp.text[:500]
                logger.warning(
                    "Dify API error (attempt %d/%d): HTTP %d - %s",
                    attempt,
                    self.config.max_retries,
                    resp.status_code,
                    error_body,
                )

                # 429 或 5xx 可以重试
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = min(2**attempt, 30)
                    time.sleep(wait)
                    continue

                # 4xx 其他错误不重试
                return {
                    "data": {
                        "status": "failed",
                        "outputs": {},
                        "error": f"HTTP {resp.status_code}: {error_body}",
                        "elapsed_time": 0,
                        "total_tokens": 0,
                    }
                }

            except requests.exceptions.Timeout:
                logger.warning(
                    "Dify API timeout (attempt %d/%d)", attempt, self.config.max_retries
                )
                last_error = requests.exceptions.Timeout(
                    f"Timeout after {self.config.timeout}s"
                )
            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    "Dify API connection error (attempt %d/%d): %s",
                    attempt,
                    self.config.max_retries,
                    str(e)[:200],
                )
                last_error = e
                wait = min(2**attempt, 30)
                time.sleep(wait)

        # 所有重试都失败
        return {
            "data": {
                "status": "failed",
                "outputs": {},
                "error": f"All {self.config.max_retries} retries failed: {last_error}",
                "elapsed_time": 0,
                "total_tokens": 0,
            }
        }

    def health_check(self) -> bool:
        """检查 Dify API 是否可达。"""
        try:
            # 试着调用一个简单的 API
            url = f"{self.config.base_url.rstrip('/')}/parameters"
            resp = self.session.get(url, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False
