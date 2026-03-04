#!/usr/bin/env python3
"""
PDF to Markdown Converter - 统一入口
支持两种模式：
1. 双击运行或无参数运行 -> 启动 Web UI
2. 带参数运行 -> 执行 CLI 转换

Usage:
    双击运行或: python main.py
    CLI 模式:   python main.py input.pdf [-o output.md] [-k API_KEY] [-u BASE_URL] [-m MODEL]
"""

import sys
import os

# 检查是否安装了必要依赖
def check_dependencies():
    required_packages = [
        ("streamlit", "streamlit"),
        ("google.genai", "google-genai"),
        ("dotenv", "python-dotenv"),
        ("fitz", "pymupdf"),
    ]
    
    missing = []
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing.append((package_name, import_name))
    
    if missing:
        print("Installing missing dependencies...")
        import subprocess
        for package_name, _ in missing:
            print(f"  Installing {package_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print("All dependencies installed!")


def main():
    # 检查依赖
    check_dependencies()
    
    # 判断启动模式
    # 如果有命令行参数（除了脚本本身），则使用 CLI 模式
    # 否则启动 Web UI
    if len(sys.argv) > 1:
        # CLI 模式
        run_cli()
    else:
        # Web UI 模式
        run_webui()


def run_webui():
    """启动 Web UI 模式"""
    import subprocess
    print("Starting PDF to Markdown Web UI...")
    print("Please open your browser to: http://localhost:8501")
    print("Press Ctrl+C to stop the server")
    
    # 获取当前目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    webui_path = os.path.join(script_dir, "webui.py")
    
    # 启动 Streamlit
    subprocess.run([sys.executable, "-m", "streamlit", "run", webui_path])


def run_cli():
    """运行 CLI 模式"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='PDF to Markdown Converter - CLI Mode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py input.pdf
  python main.py input.pdf -o output.md
  python main.py input.pdf -k YOUR_API_KEY
  python main.py ./pdfs -d
  python main.py input.pdf -u https://custom.api.com/v1
        """
    )
    
    parser.add_argument('input', help='Path to PDF file or directory containing PDF files')
    parser.add_argument('-o', '--output', help='Output directory (for batch) or file (for single)')
    parser.add_argument('-k', '--api-key', help='Gemini API key')
    parser.add_argument('-p', '--prompt', help='Custom prompt file')
    parser.add_argument('-u', '--base-url', help='Custom base URL for Gemini API')
    parser.add_argument('-m', '--model', default='gemini-3-flash-preview', help='Gemini model to use')
    parser.add_argument('-d', '--directory', '--dir', action='store_true', 
                       help='Treat input as a directory and process all PDFs in it')
    parser.add_argument('-s', '--stream', action='store_true', default=True, help='Use streaming mode')
    parser.add_argument('--no-stream', dest='stream', action='store_false', help='Disable streaming mode')
    parser.add_argument('-c', '--chunk-size', type=int, default=2, help='Pages per chunk')
    parser.add_argument('--no-chunking', dest='use_chunking', default=None, action='store_false')
    parser.add_argument('--force-chunking', dest='use_chunking', default=None, action='store_true')
    
    args = parser.parse_args()
    
    # 导入并运行 pdf2md 模块
    from pdf2md import process_single_pdf, load_prompt
    
    input_path = args.input
    
    # 获取 API key
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: Please provide API key via -k option or GEMINI_API_KEY environment variable")
        sys.exit(1)
    
    # 获取 base URL
    base_url = args.base_url or os.environ.get('BASE_URL')
    
    # 获取 model
    model_name = args.model
    
    # 加载 prompt
    prompt_file = args.prompt if args.prompt else "prompt_general.md"
    prompt = load_prompt(prompt_file)
    
    # 获取 chunking 选项
    chunk_size = args.chunk_size
    use_chunking = args.use_chunking
    
    # 判断是否为目录
    is_directory = args.directory or (os.path.isdir(input_path) if os.path.exists(input_path) else False)
    
    try:
        if is_directory:
            # 批量处理
            if not os.path.isdir(input_path):
                print(f"Error: {input_path} is not a directory")
                sys.exit(1)
            
            output_dir = args.output if args.output else input_path
            from pathlib import Path
            pdf_files = list(Path(input_path).glob("*.pdf"))
            
            if not pdf_files:
                print(f"No PDF files found in {input_path}")
                sys.exit(1)
            
            print(f"Found {len(pdf_files)} PDF files")
            print(f"Output directory: {output_dir}")
            
            success = 0
            failed = 0
            
            for pdf_file in pdf_files:
                pdf_path = str(pdf_file)
                if process_single_pdf(pdf_path, api_key, prompt, base_url, model_name, 
                                     output_dir, args.stream, chunk_size, use_chunking):
                    success += 1
                else:
                    failed += 1
            
            print(f"\n{'='*50}")
            print(f"Completed! Success: {success}, Failed: {failed}")
            print(f"Output: {output_dir}")
            
        else:
            # 单文件处理
            if not os.path.exists(input_path):
                print(f"Error: File not found: {input_path}")
                sys.exit(1)
            
            output_file = args.output if args.output else None
            
            print(f"Processing: {input_path}")
            print(f"Model: {model_name}")
            
            from pdf2md import convert_pdf_to_markdown, save_markdown
            
            markdown = convert_pdf_to_markdown(
                input_path, api_key, prompt, base_url, model_name,
                stream=args.stream, chunk_size=chunk_size, use_chunking=use_chunking
            )
            
            if output_file:
                save_markdown(markdown, output_file)
                print(f"Output saved to: {output_file}")
            else:
                # 输出到文件
                from pathlib import Path
                output_file = str(Path(input_path).with_suffix('.md'))
                save_markdown(markdown, output_file)
                print(f"Output saved to: {output_file}")
            
            print("Done!")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
