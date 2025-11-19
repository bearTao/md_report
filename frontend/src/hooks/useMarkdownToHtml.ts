import { useMemo } from 'react';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkHtml from 'remark-html';

/**
 * 将 Markdown 内容转换为 HTML
 * 
 * 使用 unified 生态系统替代 ReactMarkdown
 * 支持 GitHub Flavored Markdown (GFM)
 * 
 * @param markdown - Markdown 文本内容
 * @returns HTML 字符串
 */
export const useMarkdownToHtml = (markdown: string): string => {
  return useMemo(() => {
    if (!markdown) return '';
    
    try {
      const result = unified()
        .use(remarkParse) // 解析 Markdown 为 AST
        .use(remarkGfm)   // 支持 GFM 语法（表格、删除线等）
        .use(remarkHtml, { 
          sanitize: false  // 不进行 HTML 清理（后端内容可信）
        })
        .processSync(markdown)
        .toString();
      
      return result;
    } catch (error) {
      console.error('Markdown 转换失败:', error);
      // 降级处理：返回纯文本（用 <pre> 包裹）
      return `<pre>${markdown}</pre>`;
    }
  }, [markdown]);
};
