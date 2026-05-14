"""内容清洗与 excerpt 提取。"""

import re

from collector.models import RawItem


class ContentCleaner:
    """保守清洗内容，尽量保留 README 的语义结构。"""

    def clean(self, item: RawItem) -> str:
        if item.source_type == "github":
            return self.clean_readme(item.raw_text or "")
        return self.clean_article(item.raw_text or "")

    def clean_readme(self, raw_text: str) -> str:
        text = re.sub(r"<!--.*?-->", "", raw_text, flags=re.DOTALL)
        text = self._remove_badge_and_image_only_lines(text)
        text = self._collapse_long_install_logs(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def clean_article(self, raw_text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", raw_text or "")
        return text.strip()

    def extract_excerpt(self, content: str, max_length: int = 2000) -> str:
        if len(content) <= max_length:
            return content

        section = self._extract_preferred_section(content)
        if section and len(section) <= max_length:
            return section

        truncated = content[:max_length]
        cut_at = max(truncated.rfind("\n\n"), truncated.rfind("."), truncated.rfind("。"))
        if cut_at > int(max_length * 0.7):
            return truncated[: cut_at + 1].strip()
        return truncated.rstrip() + "..."

    def _remove_badge_and_image_only_lines(self, text: str) -> str:
        cleaned_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append(line)
                continue

            has_image = bool(re.search(r"!\[[^\]]*\]\([^)]*\)", stripped)) or "<img" in stripped.lower()
            badge_like = bool(re.search(r"shields\.io|badge|\.svg|circleci|zenodo", stripped, re.I))
            has_enough_text = bool(re.search(r"[A-Za-z\u4e00-\u9fff]{10,}", re.sub(r"<[^>]+>", "", stripped)))

            if has_image and (badge_like or not has_enough_text):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _collapse_long_install_logs(self, text: str) -> str:
        # V0 只做轻量处理：过长连续命令输出块截断，避免安装日志挤占 Dify 上下文。
        return re.sub(
            r"(```(?:bash|shell|console|sh)?\n)(.{3000,}?)(\n```)",
            lambda m: m.group(1) + m.group(2)[:1200].rstrip() + "\n# ... truncated ..." + m.group(3),
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

    def _extract_preferred_section(self, content: str) -> str:
        match = re.search(
            r"(^##\s*(?:Description|Overview|About|Introduction|简介|概述).+?)(?=^##\s|\Z)",
            content,
            flags=re.IGNORECASE | re.DOTALL | re.MULTILINE,
        )
        return match.group(1).strip() if match else ""