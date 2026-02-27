# PDF to Markdown Converter

使用 Google Gemini API 将 PDF 文件转换为 Markdown 格式。

## 功能

- 读取 PDF 文件
- 使用 `prompt.md` 中的自定义提示词
- 调用 Gemini API 进行转换
- 输出与输入文件同名的 `.md` 文件

## 使用方法

### 1. 安装依赖

```bash
pip install google-genai python-dotenv
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

### 3. 编辑 prompt.md

在 `prompt.md` 文件中添加你想要使用的提示词。

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
| `--prompt` | `-p` | 提示词文件路径（默认: prompt.md） |
| `--base-url` | `-u` | 自定义 Base URL（可选，用于代理或其他 API 端点） |
| `--model` | `-m` | 使用的模型（默认: gemini-3-flash-preview） |
| `--directory` | `-d` | 将输入作为目录，处理目录下所有 PDF 文件 |

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
```
