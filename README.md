# PDF to Markdown Converter

使用 Google Gemini AI 将 PDF 文档转换为干净的 Markdown 格式。

> 💡 **核心优势**：不仅提取文字，更能识别并保持复杂格式（表格、标题、列表、代码块等），输出标准的 Markdown，**专为 AI / LLM 处理优化**。

## 功能

- 📄 PDF 转 Markdown 转换
- 🔄 大文件分块处理（>10页自动启用）
- 📡 流式输出，避免大文件超时
- 📁 批量处理目录下的所有 PDF
- 🎨 Web UI 图形界面（支持多文件拖拽、进度跟踪、批量下载）
- ⚙️ 支持自定义提示词和模型参数
- 📊 **智能表格识别**：保持表格结构，自动转换为 Markdown 表格格式
- 🎯 **格式还原**：标题、列表、代码块等格式元素保持原样
- 🤖 **LLM 优化输出**：专为大型语言模型设计，便于后续 AI 处理和分析
- 🖼️ **图片文字识别 (OCR)**：支持扫描版 PDF 和图片中的文字提取

## 使用方法

### 命令行方式

```bash
pip install google-genai python-dotenv pymupdf tenacity
```

### 2. 配置

**方式一：.env 文件（推荐）**

1. 复制 `.env.example` 为 `.env`:
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入你的 API Key：
   ```
   GEMINI_API_KEY=你的Gemini_API密钥
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

## Web UI（推荐）

推荐使用 Web UI，界面更友好，功能更丰富：

```bash
streamlit run webui.py
```

然后打开浏览器 http://localhost:8501

### Web UI 功能

- 🎨 拖拽上传多个 PDF 文件
- 📊 实时进度显示（精确到页）
- 💾 支持批量下载（ZIP 格式）
- ⚙️ 侧边栏参数配置
- 📝 支持自定义提示词
- 🔄 转换结果保存在会话中
