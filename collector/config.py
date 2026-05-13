"""
配置管理

从环境变量加载配置，支持开发和生产环境
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CollectorConfig:
    """Collector 模块配置"""
    
    # GitHub API
    github_token: str
    github_api_timeout: int = 30
    github_max_retries: int = 3
    github_rate_limit_buffer: int = 100  # 保留配额，低于此值时等待
    
    # 通用配置
    save_raw_payload: bool = True  # 开发期保留原始响应，生产期关闭
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "CollectorConfig":
        """从环境变量加载配置"""
        github_token = os.getenv("GITHUB_TOKEN", "")
        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN is required. "
                "Please set it in .env file or environment variables."
            )
        
        return cls(
            github_token=github_token,
            github_api_timeout=int(os.getenv("GITHUB_API_TIMEOUT", "30")),
            github_max_retries=int(os.getenv("GITHUB_MAX_RETRIES", "3")),
            github_rate_limit_buffer=int(os.getenv("GITHUB_RATE_LIMIT_BUFFER", "100")),
            save_raw_payload=os.getenv("SAVE_RAW_PAYLOAD", "true").lower() == "true",
            log_level=os.getenv("COLLECTOR_LOG_LEVEL", "INFO"),
        )
    
    def validate(self) -> bool:
        """验证配置"""
        if not self.github_token:
            return False
        
        if self.github_api_timeout <= 0:
            return False
        
        if self.github_max_retries < 0:
            return False
        
        if self.github_rate_limit_buffer < 0:
            return False
        
        return True
    
    def __repr__(self) -> str:
        """安全的字符串表示（隐藏 token）"""
        token_preview = f"{self.github_token[:8]}..." if self.github_token else "None"
        return (
            f"CollectorConfig("
            f"github_token={token_preview}, "
            f"timeout={self.github_api_timeout}, "
            f"max_retries={self.github_max_retries}, "
            f"rate_limit_buffer={self.github_rate_limit_buffer}, "
            f"save_raw_payload={self.save_raw_payload}, "
            f"log_level={self.log_level})"
        )
