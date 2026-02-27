#!/usr/bin/env python3
"""
PDF to Markdown converter using Google Gemini API
Usage: python pdf2md.py <pdf_file>
"""

import os
import sys
import base64
import argparse
import json
from pathlib import Path

# Try to import google.genai, install if not available
try:
    import google.genai as genai
except ImportError:
    print("Installing google-genai...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-genai"])
    import google.genai as genai

# Try to import dotenv, install if not available
try:
    from dotenv import load_dotenv
except ImportError:
    print("Installing python-dotenv...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv

# Load .env file
load_dotenv()


def load_prompt(prompt_file: str = "prompt_v3.md") -> str:
    """Load the prompt from prompt_v3.md file"""
    prompt_path = Path(prompt_file)
    if not prompt_path.exists():
        print(f"Warning: {prompt_file} not found, using default prompt")
        return "Convert the following PDF content to well-formatted Markdown:"
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def encode_pdf_to_base64(pdf_path: str) -> str:
    """Encode PDF file to base64"""
    with open(pdf_path, 'rb') as pdf_file:
        return base64.b64encode(pdf_file.read()).decode('utf-8')


def get_output_filename(pdf_path: str) -> str:
    """Generate output markdown filename from PDF filename"""
    pdf_name = Path(pdf_path).stem
    return f"{pdf_name}.md"


def convert_pdf_to_markdown(pdf_path: str, api_key: str, prompt: str = None, base_url: str = None, model_name: str = None, stream: bool = True) -> str:
    """Convert PDF to Markdown using Gemini API
    
    Args:
        pdf_path: Path to the PDF file
        api_key: Gemini API key
        prompt: Custom prompt text
        base_url: Custom base URL
        model_name: Model to use
        stream: Use streaming mode to avoid timeouts (default: True)
    """
    from google.genai import types
    
    # Default model
    if model_name is None:
        model_name = 'gemini-3-flash-preview'
    
    # Load prompt if not provided
    if prompt is None:
        prompt = load_prompt()
    
    # Encode PDF
    pdf_data = encode_pdf_to_base64(pdf_path)
    
    # Create the prompt with PDF
    full_prompt = f"{prompt}\n\nPlease convert the following PDF to Markdown:"
    
    # Configure client - always use Client, never use configure()
    if base_url:
        http_options = types.HttpOptions(baseUrl=base_url)
        client = genai.Client(api_key=api_key, http_options=http_options)
    else:
        client = genai.Client(api_key=api_key)
    
    # Use types.Part to wrap the PDF content
    pdf_part = types.Part.from_bytes(
        data=base64.b64decode(pdf_data) if pdf_data else b'',
        mime_type='application/pdf'
    )
    text_part = types.Part.from_text(text=full_prompt)
    
    # Determine config based on model
    if model_name.startswith('gemini-3'):
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH)
        )
    else:
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=1024)
        )
    
    # Use streaming to avoid timeouts on large files
    if stream:
        print("Using streaming mode...")
        full_text = ""
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=[pdf_part, text_part],
            config=config
        ):
            if chunk.text:
                full_text += chunk.text
                print(".", end="", flush=True)
        print(" done!")
        return full_text
    else:
        # Non-streaming mode
        if model_name.startswith('gemini-3'):
            response = client.models.generate_content(
                model=model_name,
                contents=[pdf_part, text_part],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH)
                )
            )
        else:
            response = client.models.generate_content(
                model=model_name,
                contents=[pdf_part, text_part],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=1024)
                )
            )
        return response.text


def save_markdown(content: str, output_path: str):
    """Save markdown content to file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Markdown saved to: {output_path}")


def process_single_pdf(pdf_path: str, api_key: str, prompt: str, base_url: str, model_name: str, output_dir: str = None, stream: bool = True):
    """Process a single PDF file"""
    try:
        print(f"\nProcessing: {pdf_path}")
        print(f"Using model: {model_name}")
        
        # Determine output path
        if output_dir:
            pdf_name = Path(pdf_path).stem
            output_file = os.path.join(output_dir, f"{pdf_name}.md")
        else:
            output_file = get_output_filename(pdf_path)
        
        # Convert PDF to Markdown
        markdown_content = convert_pdf_to_markdown(pdf_path, api_key, prompt, base_url, model_name, stream=stream)
        
        # Save to file
        save_markdown(markdown_content, output_file)
        
        print(f"Completed: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Convert PDF to Markdown using Gemini API')
    parser.add_argument('input', help='Path to PDF file or directory containing PDF files')
    parser.add_argument('-o', '--output', help='Output directory (for batch) or file (for single)')
    parser.add_argument('-k', '--api-key', help='Gemini API key (optional, will use GEMINI_API_KEY env var if not provided)')
    parser.add_argument('-p', '--prompt', help='Custom prompt file (default: prompt_v3.md)')
    parser.add_argument('-u', '--base-url', help='Custom base URL for Gemini API (optional, will use BASE_URL env var if not provided)')
    parser.add_argument('-m', '--model', help='Gemini model to use (default: gemini-3-flash-preview)', default='gemini-3-flash-preview')
    parser.add_argument('-d', '--directory', '--dir', action='store_true', help='Treat input as a directory and process all PDFs in it')
    parser.add_argument('-s', '--stream', action='store_true', default=True, help='Use streaming mode to avoid timeouts (default: enabled)')
    parser.add_argument('--no-stream', dest='stream', action='store_false', help='Disable streaming mode')
    
    args = parser.parse_args()
    
    input_path = args.input
    
    # Get API key
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: Please provide API key via -k option, GEMINI_API_KEY in .env, or set BASE_URL environment variable")
        sys.exit(1)
    
    # Get base URL
    base_url = args.base_url or os.environ.get('BASE_URL')
    
    # Get model name
    model_name = args.model
    
    # Load prompt
    prompt_file = args.prompt if args.prompt else "prompt_v3.md"
    prompt = load_prompt(prompt_file)
    
    # Get stream option
    stream_mode = args.stream
    
    # Determine if input is a directory or file
    is_directory = args.directory or (os.path.isdir(input_path) if os.path.exists(input_path) else False)
    
    try:
        if is_directory:
            # Batch processing: process all PDFs in directory
            if not os.path.isdir(input_path):
                print(f"Error: {input_path} is not a directory")
                sys.exit(1)
            
            # Get output directory
            output_dir = args.output if args.output else input_path
            
            # Find all PDF files
            pdf_files = list(Path(input_path).glob("*.pdf"))
            
            if not pdf_files:
                print(f"No PDF files found in {input_path}")
                sys.exit(1)
            
            print(f"Found {len(pdf_files)} PDF files to process")
            print(f"Output directory: {output_dir}")
            print(f"Using model: {model_name}")
            print(f"Using prompt: {prompt_file}")
            if base_url:
                print(f"Using custom base URL: {base_url}")
            
            # Process each PDF
            success_count = 0
            fail_count = 0
            
            for pdf_file in pdf_files:
                pdf_path = str(pdf_file)
                if process_single_pdf(pdf_path, api_key, prompt, base_url, model_name, output_dir, stream=stream_mode):
                    success_count += 1
                else:
                    fail_count += 1
            
            print(f"\n{'='*50}")
            print(f"Batch processing completed!")
            print(f"Success: {success_count}, Failed: {fail_count}")
            print(f"Output files saved to: {output_dir}")
            
        else:
            # Single file processing
            if not os.path.exists(input_path):
                print(f"Error: PDF file not found: {input_path}")
                sys.exit(1)
            
            # Get output filename
            output_file = args.output if args.output else get_output_filename(input_path)
            
            print(f"Processing: {input_path}")
            print(f"Using model: {model_name}")
            print(f"Using prompt: {prompt_file}")
            if base_url:
                print(f"Using custom base URL: {base_url}")
            
            # Convert PDF to Markdown
            markdown_content = convert_pdf_to_markdown(input_path, api_key, prompt, base_url, model_name, stream=stream_mode)
            
            # Save to file
            save_markdown(markdown_content, output_file)
            
            print("Conversion completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
