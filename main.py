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
import time
import threading

# 检查是否在 PyInstaller 打包环境中运行
def is_frozen():
    """检测是否在打包后的 exe 中运行"""
    return getattr(sys, 'frozen', False)

# 获取 Python 解释器路径
def get_python_executable():
    """获取正确的 Python 解释器路径"""
    if is_frozen():
        # 打包后的 exe，从 exe 所在目录找 python.exe
        exe_dir = os.path.dirname(sys.executable)
        # 在 Windows 上，PyInstaller 打包的 exe 旁边可能有 python DLL
        # 我们需要找到系统 Python
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), 'python.exe'),
            r'C:\Users\AAA-110\AppData\Local\Programs\Python\Python314\python.exe',
            r'C:\Program Files\Python314\python.exe',
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        # 如果都找不到，尝试用原来的
        return sys.executable
    return sys.executable

# 检查是否安装了必要依赖
def check_dependencies():
    # 如果是打包后的 exe，依赖已经包含在内，跳过检查
    if is_frozen():
        return
    
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


def monitor_process(process, process_name):
    """监控子进程，如果退出则通知用户"""
    return_code = process.wait()
    if return_code != 0:
        print(f"\n[ERROR] {process_name} exited with code {return_code}")
        print("Check the output above for more details.")
    else:
        print(f"\n[INFO] {process_name} stopped")


def run_webui():
    """启动 Web UI 模式"""
    import subprocess
    import webbrowser
    
    print("=" * 60)
    print("PDF to Markdown Converter - Web UI Mode")
    print("=" * 60)
    print("Starting Streamlit server...")
    
    # 获取当前目录
    if is_frozen():
        # 打包后的 exe，使用 _MEIPASS 获取资源路径
        script_dir = sys._MEIPASS
        print(f"[DEBUG] Running as frozen exe, script_dir: {script_dir}")
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"[DEBUG] Running as script, script_dir: {script_dir}")
    
    webui_path = os.path.join(script_dir, "webui.py")
    print(f"[DEBUG] webui_path: {webui_path}")
    print(f"[DEBUG] webui exists: {os.path.exists(webui_path)}")
    
    # 获取正确的 Python 解释器
    python_exe = get_python_executable()
    print(f"[DEBUG] python_exe: {python_exe}")
    
    # 启动 Streamlit（显示输出以便调试）
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    # 使用正确的 Python 解释器
    process = subprocess.Popen(
        [python_exe, "-m", "streamlit", "run", webui_path, 
         "--server.headless=true",
         "--server.port=8501",
         "--server.address=127.0.0.1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        bufsize=1,
        cwd=script_dir  # 设置工作目录
    )
    
    # 启动线程监控进程
    monitor_thread = threading.Thread(target=monitor_process, args=(process, "Streamlit"))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    print("\nWaiting for Streamlit to start...")
    print("If this takes too long, check the output below for errors.")
    
    # 读取输出直到服务启动
    started = False
    startup_timeout = 15  # 15秒超时
    start_time = time.time()
    
    while time.time() - start_time < startup_timeout:
        line = process.stdout.readline()
        if line:
            print(f"[Streamlit] {line.rstrip()}")
            if "Running on" in line or "URL" in line or "http://127.0.0.1:8501" in line:
                started = True
                break
            # 检查错误
            if "Error" in line or "error" in line or "Exception" in line:
                print(f"[WARNING] Possible error detected: {line}")
        
        # 检查进程是否已退出
        if process.poll() is not None:
            print(f"[ERROR] Streamlit process exited prematurely with code {process.returncode}")
            # 读取剩余输出
            remaining = process.stdout.read()
            if remaining:
                print(remaining)
            break
        
        time.sleep(0.1)
    
    if started:
        print("\n" + "=" * 60)
        print("Web UI is running!")
        print("Please open your browser to: http://localhost:8501")
        print("Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # 打开浏览器
        webbrowser.open("http://localhost:8501")
        
        # 保持运行
        try:
            while True:
                # 继续读取输出
                line = process.stdout.readline()
                if line:
                    print(f"[Streamlit] {line.rstrip()}")
                
                # 检查进程状态
                if process.poll() is not None:
                    print("[INFO] Streamlit server stopped")
                    break
                
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nStopping server...")
            process.terminate()
            process.wait()
    else:
        print("\n[ERROR] Streamlit failed to start within timeout")
        print("Check the output above for errors")
        process.terminate()
    
    print("\nPress Enter to exit...")
    try:
        input()
    except:
        pass


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
