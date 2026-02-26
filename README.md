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
| `pdf_file` | - | 输入的 PDF 文件路径（必需） |
| `--output` | `-o` | 输出的 Markdown 文件路径（可选，默认与 PDF 同名） |
| `--api-key` | `-k` | Gemini API 密钥 |
| `--prompt` | `-p` | 提示词文件路径（默认: prompt.md） |
| `--base-url` | `-u` | 自定义 Base URL（可选，用于代理或其他 API 端点） |

## 示例

```bash
# 将 document.pdf 转换为 document.md
python pdf2md.py document.pdf

# 带 API Key
python pdf2md.py document.pdf -k AIzaSy...
```
