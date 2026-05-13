"""
GitHubCollector 实现

负责从 GitHub API 采集 repos 数据
"""

import time
import math
import httpx
from datetime import datetime, timezone
from typing import Iterable, Dict, Any, Optional, Set

from collector.base import (
    BaseCollector,
    CollectorError,
    RateLimitExceeded,
    AuthenticationError,
    ResourceNotFound
)
from collector.models import SourceQuery, RawItem
from collector.config import CollectorConfig
from collector.utils import (
    logger,
    parse_github_datetime,
    truncate_text,
    sanitize_url,
    retry_with_backoff
)


class GitHubCollector(BaseCollector):
    """GitHub 采集器"""
    
    # GitHub API sort 参数映射
    SORT_MAPPING = {
        "best_match": None,  # 不传 sort，使用默认相关性排序
        "stars": "stars",
        "forks": "forks",
        "updated": "updated",
        "help-wanted-issues": "help-wanted-issues"
    }
    
    def __init__(self, config: CollectorConfig):
        super().__init__(config)
        
        # 初始化 httpx 客户端
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"token {config.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "SocialMediaReader/0.1"
            },
            timeout=config.github_api_timeout
        )
        
        self.rate_limit_buffer = config.github_rate_limit_buffer
        
        # 初始化 rate limit 状态
        self.remaining = 5000  # 默认值
        self.reset_at = 0
        self.limit = 5000
        
        # 启动时获取真实 rate limit 状态
        self._fetch_rate_limit_status()
        
        logger.info(f"GitHubCollector initialized: {self.get_rate_limit_status()}")
    
    def _fetch_rate_limit_status(self):
        """启动时获取当前 rate limit 状态"""
        try:
            response = self.client.get("/rate_limit")
            if response.status_code == 200:
                data = response.json()
                core = data["resources"]["core"]
                self.remaining = core["remaining"]
                self.reset_at = core["reset"]
                self.limit = core["limit"]
                logger.info(
                    f"Rate limit initialized: {self.remaining}/{self.limit}, "
                    f"resets at {datetime.fromtimestamp(self.reset_at)}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch rate limit status: {e}")
            # 保持默认值
    
    def _update_rate_limit(self, headers: httpx.Headers):
        """从响应头更新 rate limit 状态"""
        try:
            if "X-RateLimit-Remaining" in headers:
                self.remaining = int(headers["X-RateLimit-Remaining"])
            if "X-RateLimit-Reset" in headers:
                self.reset_at = int(headers["X-RateLimit-Reset"])
            if "X-RateLimit-Limit" in headers:
                self.limit = int(headers["X-RateLimit-Limit"])
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
    
    def _check_rate_limit(self):
        """检查速率限制，必要时等待"""
        if self.remaining < self.rate_limit_buffer:
            wait_seconds = self.reset_at - time.time()
            if wait_seconds > 0:
                logger.warning(
                    f"Rate limit approaching ({self.remaining}/{self.limit}), "
                    f"waiting {wait_seconds:.0f}s until reset"
                )
                time.sleep(wait_seconds + 1)
                # 等待后重新获取状态
                self._fetch_rate_limit_status()
    
    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        """统一处理响应，包括 rate limit"""
        # 更新 rate limit 状态
        self._update_rate_limit(response.headers)
        
        # 处理 401 认证失败
        if response.status_code == 401:
            raise AuthenticationError("GitHub authentication failed. Check your token.")
        
        # 处理 403 rate limit exceeded
        if response.status_code == 403:
            if "rate limit exceeded" in response.text.lower():
                wait_seconds = self.reset_at - time.time()
                logger.error(
                    f"Rate limit exceeded (403), waiting {wait_seconds:.0f}s"
                )
                if wait_seconds > 0:
                    time.sleep(wait_seconds + 1)
                    self._fetch_rate_limit_status()
                raise RateLimitExceeded("GitHub rate limit exceeded")
        
        # 处理 404
        if response.status_code == 404:
            raise ResourceNotFound(f"Resource not found: {response.url}")
        
        # 处理其他错误
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise CollectorError(f"GitHub API error: {e}")
        
        return response
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """获取速率限制状态"""
        return {
            "remaining": self.remaining,
            "limit": self.limit,
            "reset_at": self.reset_at,
            "reset_at_datetime": datetime.fromtimestamp(self.reset_at).isoformat(),
            "buffer": self.rate_limit_buffer
        }
    
    def collect(self, query: SourceQuery) -> Iterable[RawItem]:
        """
        执行采集任务
        
        Args:
            query: 采集查询参数
        
        Yields:
            RawItem 迭代器
        """
        if query.source_type != "github":
            raise ValueError(f"GitHubCollector only supports source_type='github', got '{query.source_type}'")
        
        logger.info(f"Starting collection for query: {query}")
        
        # 单次采集内去重
        seen_repos: Set[str] = set()
        
        for keyword in query.keywords:
            logger.info(f"Searching for keyword: '{keyword}'")
            
            for rank, raw_item in enumerate(self._search_repos(keyword, query), start=1):
                # 去重
                if raw_item.external_id in seen_repos:
                    logger.debug(f"Skipping duplicate: {raw_item.external_id}")
                    continue
                
                seen_repos.add(raw_item.external_id)
                raw_item.rank = rank
                raw_item.query_keyword = keyword
                
                yield raw_item
                
                # 检查是否达到最大数量
                if len(seen_repos) >= query.max_items:
                    logger.info(f"Reached max_items limit: {query.max_items}")
                    return
        
        logger.info(f"Collection completed. Total items: {len(seen_repos)}")
    
    def _search_repos(self, keyword: str, query: SourceQuery) -> Iterable[RawItem]:
        """
        搜索 repos，处理分页
        
        Args:
            keyword: 搜索关键词
            query: 查询参数
        
        Yields:
            RawItem 迭代器
        """
        # 构造搜索查询
        q_parts = [keyword]
        
        if query.programming_language:
            q_parts.append(f"language:{query.programming_language}")
        
        if query.min_stars > 0:
            q_parts.append(f"stars:>={query.min_stars}")
        
        for topic in query.topics:
            q_parts.append(f"topic:{topic}")
        
        if query.time_range:
            start, end = query.time_range
            q_parts.append(f"created:{start.strftime('%Y-%m-%d')}..{end.strftime('%Y-%m-%d')}")
        
        q = " ".join(q_parts)
        
        logger.debug(f"GitHub search query: {q}")
        
        # 分页采集
        page = 1
        collected = 0
        
        while collected < query.max_items:
            self._check_rate_limit()
            
            # 构造请求参数
            params = {
                "q": q,
                "per_page": min(query.page_size, query.max_items - collected),
                "page": page
            }
            
            # 只有非 best_match 时才传 sort
            github_sort = self.SORT_MAPPING.get(query.sort_by)
            if github_sort is not None:
                params["sort"] = github_sort
                params["order"] = "desc"
            
            logger.debug(f"Fetching page {page} with params: {params}")
            
            try:
                response = self.client.get("/search/repositories", params=params)
                self._handle_response(response)
            except (RateLimitExceeded, AuthenticationError) as e:
                logger.error(f"Fatal error during search: {e}")
                raise
            except CollectorError as e:
                logger.error(f"Error during search: {e}")
                break
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                logger.info(f"No more results for keyword '{keyword}'")
                break
            
            logger.info(f"Page {page}: got {len(items)} repos")
            
            for repo_data in items:
                try:
                    raw_item = self._parse_repo(repo_data, query)
                    yield raw_item
                    collected += 1
                    
                    if collected >= query.max_items:
                        return
                except Exception as e:
                    logger.error(f"Failed to parse repo {repo_data.get('full_name')}: {e}")
                    continue
            
            # GitHub Search API 最多返回 1000 条结果（100 页 * 10 per_page）
            if page >= 100 or len(items) < params["per_page"]:
                logger.info("Reached end of search results")
                break
            
            page += 1
    
    def _parse_repo(self, repo_data: Dict[str, Any], query: SourceQuery) -> RawItem:
        """
        解析 repo 数据为 RawItem
        
        Args:
            repo_data: GitHub API 返回的 repo 数据
            query: 查询参数
        
        Returns:
            RawItem
        """
        full_name = repo_data["full_name"]
        owner = repo_data["owner"]["login"]
        
        # 获取 README（可选，V0 阶段可以跳过以节省 API 配额）
        readme_text = None
        readme_truncated = False
        readme_length = 0
        
        if self.config.save_raw_payload:
            # 开发期获取 README
            try:
                readme_text, readme_truncated, readme_length = self._fetch_readme(full_name)
            except Exception as e:
                logger.warning(f"Failed to fetch README for {full_name}: {e}")
        
        # 解析时间
        created_at = parse_github_datetime(repo_data.get("created_at"))
        updated_at = parse_github_datetime(repo_data.get("updated_at"))
        pushed_at = parse_github_datetime(repo_data.get("pushed_at"))
        
        # 计算活跃度评分
        activity_score = self._calculate_activity_score(repo_data)
        
        # 构造元数据
        metadata = {
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "watchers": repo_data.get("watchers_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "language": repo_data.get("language"),
            "topics": repo_data.get("topics", []),
            "license": repo_data.get("license", {}).get("spdx_id") if repo_data.get("license") else None,
            "is_fork": repo_data.get("fork", False),
            "is_archived": repo_data.get("archived", False),
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "pushed_at": pushed_at.isoformat() if pushed_at else None,
            "activity_score": activity_score,
            "homepage": repo_data.get("homepage"),
        }
        
        return RawItem(
            topic_id=query.topic_id,
            source_type="github",
            source_subtype="github_repo",
            external_id=f"github:{full_name}",
            url=repo_data["html_url"],
            canonical_url=sanitize_url(repo_data["html_url"]),
            title=repo_data["name"],
            author=owner,
            description=repo_data.get("description") or "",
            published_at=created_at,
            collected_at=datetime.now(timezone.utc),
            raw_text=readme_text,
            raw_text_truncated=readme_truncated,
            raw_text_length=readme_length,
            metadata=metadata,
            collected_by="GitHubCollector",
            raw_payload=repo_data if self.config.save_raw_payload else None
        )
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    def _fetch_readme(self, full_name: str) -> tuple[str, bool, int]:
        """
        获取 repo 的 README
        
        Args:
            full_name: owner/repo
        
        Returns:
            (readme_text, is_truncated, original_length)
        """
        self._check_rate_limit()
        
        response = self.client.get(f"/repos/{full_name}/readme")
        self._handle_response(response)
        
        data = response.json()
        
        # README 内容是 base64 编码的
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        
        return truncate_text(content, max_length=5000)
    
    def _calculate_activity_score(self, repo_data: Dict[str, Any]) -> float:
        """
        计算活跃度评分（V0 简化版，不依赖历史数据）
        
        Args:
            repo_data: GitHub API 返回的 repo 数据
        
        Returns:
            活跃度评分（0-1）
        """
        now = datetime.now(timezone.utc)
        
        # 1. 最近推送新鲜度（0-1）
        pushed_at = parse_github_datetime(repo_data.get("pushed_at"))
        if pushed_at:
            days_since_push = (now - pushed_at).days
            push_freshness = max(0, 1 - days_since_push / 365)
        else:
            push_freshness = 0
        
        # 2. Stars 权重（对数归一化，0-1）
        stars = repo_data.get("stargazers_count", 0)
        stars_weight = min(1.0, math.log10(stars + 1) / 5)
        
        # 3. 是否有近期活动（90 天内）
        has_recent_activity = 1.0 if pushed_at and days_since_push < 90 else 0.0
        
        # V0 简化权重（去掉 release_freshness）
        score = (
            push_freshness * 0.5 +      # 推送新鲜度
            stars_weight * 0.3 +         # Stars 权重
            has_recent_activity * 0.2    # 近期活动
        )
        
        return round(score, 3)
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'client'):
            self.client.close()
