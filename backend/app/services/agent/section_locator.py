"""
章节定位器

本模块提供 Markdown 章节的精确解析和定位功能。

核心功能：
- 解析 Markdown 文档的章节结构
- 根据路径定位章节
- 提取章节内容预览
"""
import re
from typing import List, Optional
from loguru import logger

from app.schemas.modification_schemas import Section


class SectionLocator:
    """章节定位器（后端精确处理）"""
    
    def parse_markdown_structure(self, markdown: str) -> List[Section]:
        """
        精确解析 Markdown 结构
        
        Args:
            markdown: Markdown 文本
        
        Returns:
            List[Section]: 所有章节的详细信息
        """
        sections = []
        lines = markdown.split('\n')
        
        for i, line in enumerate(lines):
            # 匹配标题：# 至 ###### 加空格加标题文本
            if match := re.match(r'^(#{1,6})\s+(.+)$', line.strip()):
                level = len(match.group(1))
                title = match.group(2).strip()
                
                section = Section(
                    id=f"L{i+1}",  # 使用行号生成唯一 ID（1-indexed）
                    level=level,
                    title=title,
                    path="",  # 稍后构建
                    start_line=i,
                    end_line=self._find_section_end(lines, i, level),
                    parent_id=self._find_parent_id(sections, level)
                )
                
                sections.append(section)
        
        # 构建完整路径
        for section in sections:
            section.path = self._build_path(sections, section)
        
        # 计算子章节数量
        for section in sections:
            section.subsections_count = sum(
                1 for s in sections if s.parent_id == section.id
            )
        
        logger.info(f"解析 Markdown 结构完成，共 {len(sections)} 个章节")
        return sections
    
    def _find_section_end(
        self, 
        lines: List[str], 
        start: int, 
        level: int
    ) -> int:
        """
        查找章节结束行号
        
        规则：下一个同级或更高级标题的位置
        
        Args:
            lines: 所有行
            start: 起始行号
            level: 当前标题级别
        
        Returns:
            int: 结束行号（不包含）
        """
        for i in range(start + 1, len(lines)):
            line = lines[i].strip()
            if match := re.match(r'^(#{1,6})\s+', line):
                current_level = len(match.group(1))
                if current_level <= level:
                    return i
        
        return len(lines)
    
    def _find_parent_id(
        self, 
        sections: List[Section], 
        level: int
    ) -> Optional[str]:
        """
        查找父章节 ID
        
        Args:
            sections: 已解析的章节列表
            level: 当前标题级别
        
        Returns:
            Optional[str]: 父章节 ID 或 None
        """
        if level == 1:
            return None
        
        # 从后往前找第一个级别比当前小的章节
        for section in reversed(sections):
            if section.level < level:
                return section.id
        
        return None
    
    def _build_path(
        self, 
        sections: List[Section], 
        current: Section
    ) -> str:
        """
        构建完整路径
        
        示例：预分析报告->1、网格概述->1.1 网格评分分析
        
        Args:
            sections: 所有章节列表
            current: 当前章节
        
        Returns:
            str: 完整路径
        """
        path_parts = [current.title]
        parent_id = current.parent_id
        
        while parent_id:
            parent = next((s for s in sections if s.id == parent_id), None)
            if parent:
                path_parts.insert(0, parent.title)
                parent_id = parent.parent_id
            else:
                break
        
        return "->".join(path_parts)
    
    def locate_section_by_path(
        self, 
        sections: List[Section],
        path: str
    ) -> Section:
        """
        根据路径定位章节
        
        Args:
            sections: 所有章节列表
            path: 章节路径（LLM 返回的）
        
        Returns:
            Section: 定位到的章节
        
        Raises:
            ValueError: 路径不唯一或不存在
        """
        # 1. 精确匹配
        exact_match = next(
            (s for s in sections if s.path == path),
            None
        )
        
        if exact_match:
            logger.debug(f"精确匹配章节: {path}")
            return exact_match
        
        # 2. 标准化匹配（去除编号、空格差异）
        normalized_path = self._normalize_path(path)
        
        candidates = [
            s for s in sections 
            if self._normalize_path(s.path) == normalized_path
        ]
        
        if len(candidates) == 1:
            logger.warning(f"使用标准化匹配定位章节: {path} -> {candidates[0].path}")
            return candidates[0]
        
        # 3. 路径末段匹配（兜底）
        path_parts = path.split('->')
        target_title = self._normalize_title(path_parts[-1])
        
        candidates = [
            s for s in sections 
            if self._normalize_title(s.title) == target_title
        ]
        
        if len(candidates) == 1:
            logger.warning(f"使用标题匹配定位章节: {path} -> {candidates[0].path}")
            return candidates[0]
        elif len(candidates) > 1:
            raise ValueError(f"章节路径不唯一: {path}，匹配到 {len(candidates)} 个结果")
        else:
            raise ValueError(f"章节不存在: {path}")
    
    def _normalize_path(self, path: str) -> str:
        """
        标准化路径（去除编号等）
        
        Args:
            path: 原始路径
        
        Returns:
            str: 标准化后的路径
        """
        parts = path.split('->')
        normalized_parts = [self._normalize_title(p) for p in parts]
        return "->".join(normalized_parts)
    
    def _normalize_title(self, title: str) -> str:
        """
        标准化标题
        
        - 去除前导编号：1、1.1、1.1.1 等
        - 转小写
        - 去除多余空格
        
        Args:
            title: 原始标题
        
        Returns:
            str: 标准化后的标题
        """
        # 去除常见编号格式
        title = re.sub(r'^\d+[\.\、]\s*', '', title)
        title = re.sub(r'^\d+\.\d+\s*', '', title)
        title = re.sub(r'^\d+\.\d+\.\d+\s*', '', title)
        
        # 统一空格
        title = re.sub(r'\s+', ' ', title)
        
        return title.strip().lower()
    
    def extract_content_preview(
        self,
        markdown: str,
        start_line: int,
        end_line: int,
        max_chars: int = 200
    ) -> str:
        """
        提取内容预览
        
        Args:
            markdown: Markdown 文本
            start_line: 起始行号
            end_line: 结束行号
            max_chars: 最大字符数
        
        Returns:
            str: 内容预览
        """
        lines = markdown.split('\n')
        section_lines = lines[start_line:end_line]
        content = '\n'.join(section_lines)
        
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        
        return content
    
    def build_section_structure_for_llm(self, markdown: str) -> str:
        """
        构建章节结构的文本表示（给 LLM 看）
        
        Returns:
            预分析报告
            ├─ 1、网格概述
            │  ├─ 1.1 网格评分分析
            │  └─ 1.2 网格基本信息
            └─ 2、问题分析
               └─ 2.1 高负荷分析
        """
        sections = self.parse_markdown_structure(markdown)
        
        if not sections:
            return "（无章节）"
        
        lines = []
        for i, section in enumerate(sections):
            # 计算缩进
            indent = "  " * (section.level - 1)
            
            # 判断是否是最后一个子节点
            is_last = self._is_last_sibling(section, sections)
            prefix = "└─ " if is_last else "├─ "
            
            # 对于非顶级节点，添加连接线
            if section.level > 1:
                # 构建父节点的连接线
                parent_prefixes = []
                current_parent_id = section.parent_id
                level_tracker = section.level - 1
                
                while current_parent_id and level_tracker > 0:
                    parent = next((s for s in sections if s.id == current_parent_id), None)
                    if parent:
                        is_parent_last = self._is_last_sibling(parent, sections)
                        parent_prefixes.insert(0, "   " if is_parent_last else "│  ")
                        current_parent_id = parent.parent_id
                        level_tracker -= 1
                    else:
                        break
                
                line = "".join(parent_prefixes) + prefix + section.title
            else:
                line = section.title
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _is_last_sibling(self, section: Section, all_sections: List[Section]) -> bool:
        """
        判断是否是同级最后一个节点
        
        Args:
            section: 当前章节
            all_sections: 所有章节列表
        
        Returns:
            bool: 是否是最后一个
        """
        # 找出同一父节点下的所有兄弟节点
        siblings = [
            s for s in all_sections 
            if s.parent_id == section.parent_id and s.level == section.level
        ]
        
        if not siblings:
            return True
        
        # 检查当前节点是否是最后一个
        return siblings[-1].id == section.id
