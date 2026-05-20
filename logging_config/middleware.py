"""FastAPI 请求日志中间件。"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的详细信息。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        # 请求信息
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            status_code = response.status_code

            # 根据状态码选择日志级别
            if status_code >= 500:
                log_level = logging.ERROR
            elif status_code >= 400:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO

            logger.log(
                log_level,
                "%s %s %s → %d (%.1fms) [%s]",
                method,
                path,
                f"?{query}" if query else "",
                status_code,
                duration_ms,
                client_ip,
            )

            return response

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "%s %s → EXCEPTION (%.1fms) [%s]: %s",
                method,
                path,
                duration_ms,
                client_ip,
                str(exc),
                exc_info=True,
            )
            raise
