"""Dify 客户端配置。"""

import os
from dataclasses import dataclass


@dataclass
class DifyConfig:
    """Dify API 配置。

    Attributes:
        base_url: Dify API 地址，例如 http://localhost/v1
        api_key: Dify 工作流应用的 API Key
        timeout: 请求超时（秒），工作流可能耗时较长
        max_retries: 最大重试次数
    """

    base_url: str = "http://localhost/v1"
    api_key: str = ""
    timeout: int = 120
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "DifyConfig":
        return cls(
            base_url=os.getenv("DIFY_BASE_URL", "http://localhost/v1"),
            api_key=os.getenv("DIFY_API_KEY", ""),
            timeout=int(os.getenv("DIFY_TIMEOUT", "120")),
            max_retries=int(os.getenv("DIFY_MAX_RETRIES", "3")),
        )

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError(
                "DIFY_API_KEY is required. "
                "Get it from Dify: App → API Access → API Key"
            )
