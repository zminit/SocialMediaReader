"""API 配置。"""

import os
from dataclasses import dataclass


@dataclass
class APIConfig:
    """FastAPI 应用配置。"""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    title: str = "SocialMediaReader API"
    version: str = "0.1.0"

    # CORS
    cors_origins: list = None  # type: ignore

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]

    @classmethod
    def from_env(cls) -> "APIConfig":
        origins_str = os.environ.get("API_CORS_ORIGINS", "*")
        origins = [o.strip() for o in origins_str.split(",") if o.strip()]
        return cls(
            host=os.environ.get("API_HOST", "0.0.0.0"),
            port=int(os.environ.get("API_PORT", "8000")),
            debug=os.environ.get("API_DEBUG", "false").lower() in ("true", "1", "yes"),
            cors_origins=origins,
        )
