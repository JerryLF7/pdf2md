# PDF to Markdown Converter

使用 Google Gemini API 将 PDF 文件转换为 Markdown 格式。

## 功能

- 读取 PDF 文件
- 使用自定义提示词（默认: `prompt_v4.md`）
- 调用 Gemini API 进行转换
- 输出与输入文件同名的 `.md` 文件
- **大文件分块处理**：自动将长 PDF（>10页）分块处理，避免 token 限制和超时
- **流式输出**：避免大文件转换超时
- **批量处理**：支持目录批量转换

## 使用方法

### 1. 安装依赖

```bash
pip install google-genai python-dotenv pymupdf tenacity
```

### 2. 配置

**方式一：.env 文件（推荐）**

1. 复制 `.env.example` 为 `.env`:
   ```bash
   copy .env.example .env
   ```

2. 编辑 `.env` 文件:
   ```
   # 必需：API Key
   GEMINI_API_KEY=你的API密钥
   
   # 可选：自定义 Base URL（用于代理或其他 API 端点）
   # BASE_URL=https://api.example.com/v1
   ```

**方式二：环境变量**
```bash
set GEMINI_API_KEY=你的API密钥
set BASE_URL=https://api.example.com/v1
```

**方式三：命令行参数**
```bash
python pdf2md.py input.pdf -k 你的API密钥 -u https://api.example.com/v1
```

### 3. 编辑提示词文件

在 `prompt_v4.md` 文件中添加你想要使用的提示词。提示词模板支持以下占位符：

- `{PREV_CONTEXT}` 或 `{PREVIOUS_CONTEXT}` - 上一页输出的最后 500 字符（用于上下文衔接）
- `{PDF_CONTENT}` 或 `{CURRENT_PDF_CONTENT}` - 当前 PDF 页面内容

### 4. 运行脚本

```bash
# 基本用法
python pdf2md.py input.pdf

# 指定输出文件名
python pdf2md.py input.pdf -o output.md

# 指定 API Key
python pdf2md.py input.pdf -k 你的API密钥

# 指定自定义提示词文件
python pdf2md.py input.pdf -p my_prompt.md
```

## 参数说明

| 参数 | 简写 | 说明 |
|------|------|------|
| `input` | - | 输入的 PDF 文件路径或目录（必需） |
| `--output` | `-o` | 输出目录（批量处理时）或输出文件（单文件时） |
| `--api-key` | `-k` | Gemini API 密钥 |
| `--prompt` | `-p` | 提示词文件路径（默认: prompt_v4.md） |
| `--base-url` | `-u` | 自定义 Base URL（可选，用于代理或其他 API 端点） |
| `--model` | `-m` | 使用的模型（默认: gemini-3-flash-preview） |
| `--directory` | `-d` | 将输入作为目录，处理目录下所有 PDF 文件 |
| `--stream` / `--no-stream` | `-s` | 启用/禁用流式模式（默认: 启用） |
| `--chunk-size` | `-c` | 每块页数，用于大文件分块（默认: 2） |
| `--no-chunking` | - | 禁用自动分块处理 |
| `--force-chunking` | - | 强制对所有 PDF 启用分块处理 |

## 分块处理说明

对于大型 PDF 文件（>10 页），脚本会自动启用分块处理：

- **自动模式**：PDF 超过 10 页自动启用分块
- **上下文衔接**：每个分块会携带上一页输出的最后 500 字符
- **重试机制**：使用指数退避策略处理 503/429 错误
- **缝合逻辑**：自动处理跨页表格和断句合并

### 分块相关示例

```bash
# 使用默认分块大小（每块 2 页）
python pdf2md.py large_document.pdf

# 自定义分块大小（每块 1 页，更精细的处理）
python pdf2md.py large_document.pdf -c 1

# 强制对所有 PDF 启用分块（即使是小文件）
python pdf2md.py document.pdf --force-chunking

# 禁用自动分块
python pdf2md.py document.pdf --no-chunking

# 组合使用：强制分块 + 每块 1 页
python pdf2md.py document.pdf --force-chunking -c 1
```

## 示例

```bash
# 单文件转换
python pdf2md.py document.pdf

# 批量处理：转换目录下所有 PDF 文件
python pdf2md.py ./pdfs

# 批量处理：指定输出目录
python pdf2md.py ./pdfs -o ./output

# 批量处理：使用 -d 参数明确指定目录模式
python pdf2md.py ./pdfs -d

# 使用流式模式（默认启用）
python pdf2md.py document.pdf -s

# 禁用流式模式
python pdf2md.py document.pdf --no-stream

# 指定自定义模型
python pdf2md.py document.pdf -m gemini-2.0-flash-exp
```
