技术规范：长 PDF 高保真转录 Markdown 工具
1. 核心目标
解决处理 100 页以上长 PDF 时遇到的 Token 输出限制、503 服务超时 以及 跨页内容（尤其是表格）断裂 的问题。实现“复印机级别”的逐字转录。

2. Python 脚本实现思路
A. 分页分块处理 (Chunking)
库选择：使用 PyMuPDF (fitz) 进行 PDF 解析。
分块逻辑：循环遍历 PDF，建议每 1-2 页 作为一个分块（Chunk）发送给 API。
上下文衔接：每次请求时，提取上一个分块输出结果的最后 500 个字符，作为 PREV_CONTEXT 传入下一个请求。
B. 健壮性与错误处理
重试机制：由于长文档生成时间长，必须实现指数退避重试（Exponential Backoff）。推荐使用 tenacity 库。
针对性报错处理：专门处理 503 (Service Unavailable) 和 429 (Rate Limit) 错误，遇到此类错误时自动等待并重试，而不是直接崩溃。
C. 缝合逻辑 (Stitching)
表格修复：在拼接两页内容时，如果后一页是表格的延续，需确保有表头以正常渲染。
断句合并：拼接时检查：如果前一块末尾不是句号且后一块开头是小写字母，则删除中间多余的换行符，保持句子完整。
3. Prompt 模板化方案
要求：保持 Prompt 作为独立文件，脚本通过占位符动态注入内容。

A. Python 脚本中的调用逻辑
脚本应读取 prompt_v4.md 内容，并使用 .format() 或 .replace() 替换占位符：

*.py
Python
# 伪代码示例
prompt_template = open('prompt.txt').read()
final_prompt = prompt_template.format(
    PREV_CONTEXT=last_500_chars_of_previous_output,
    PDF_CONTENT=current_page_text
)

1. 给 Coding Agent 的特别提示
并发控制：根据 API 的 RPM (每分钟请求数) 限制，使用 ThreadPoolExecutor 控制并发，避免请求过快。
