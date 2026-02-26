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


def load_prompt(prompt_file: str = "prompt.md") -> str:
    """Load the prompt from prompt.md file"""
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


def convert_pdf_to_markdown(pdf_path: str, api_key: str, prompt: str = None, base_url: str = None, model_name: str = None) -> str:
    """Convert PDF to Markdown using Gemini API"""
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
    
    # Configure client
    if base_url:
        http_options = types.HttpOptions(baseUrl=base_url)
        client = genai.Client(api_key=api_key, http_options=http_options)
    else:
        genai.configure(api_key=api_key)
        client = genai.Client(api_key=api_key)
    
    # Use types.Part to wrap the PDF content
    pdf_part = types.Part.from_bytes(
        data=base64.b64decode(pdf_data) if pdf_data else b'',
        mime_type='application/pdf'
    )
    text_part = types.Part.from_text(text=full_prompt)
    
    # Check if model is gemini-3 series (uses thinking_level instead of thinking_budget)
    if model_name.startswith('gemini-3'):
        # Gemini 3 series uses thinking_level with enum
        response = client.models.generate_content(
            model=model_name,
            contents=[pdf_part, text_part],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH)
            )
        )
    else:
        # Other models use thinking_config
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


def main():
    parser = argparse.ArgumentParser(description='Convert PDF to Markdown using Gemini API')
    parser.add_argument('pdf_file', help='Path to the PDF file')
    parser.add_argument('-o', '--output', help='Output markdown file (optional, default: same name as PDF)')
    parser.add_argument('-k', '--api-key', help='Gemini API key (optional, will use GEMINI_API_KEY env var if not provided)')
    parser.add_argument('-p', '--prompt', help='Custom prompt file (default: prompt.md)')
    parser.add_argument('-u', '--base-url', help='Custom base URL for Gemini API (optional, will use BASE_URL env var if not provided)')
    parser.add_argument('-m', '--model', help='Gemini model to use (default: gemini-3-flash-preview)', default='gemini-3-flash-preview')
    
    args = parser.parse_args()
    
    # Check if PDF file exists
    if not os.path.exists(args.pdf_file):
        print(f"Error: PDF file not found: {args.pdf_file}")
        sys.exit(1)
    
    # Get API key
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: Please provide API key via -k option, GEMINI_API_KEY in .env, or BASE_URL environment variable")
        sys.exit(1)
    
    # Get base URL
    base_url = args.base_url or os.environ.get('BASE_URL')
    
    # Get model name
    model_name = args.model
    
    # Load prompt
    prompt_file = args.prompt if args.prompt else "prompt.md"
    prompt = load_prompt(prompt_file)
    
    # Get output filename
    output_file = args.output if args.output else get_output_filename(args.pdf_file)
    
    try:
        print(f"Processing: {args.pdf_file}")
        print(f"Using model: {model_name}")
        print(f"Using prompt: {prompt_file}")
        if base_url:
            print(f"Using custom base URL: {base_url}")
        
        # Convert PDF to Markdown
        markdown_content = convert_pdf_to_markdown(args.pdf_file, api_key, prompt, base_url, model_name)
        
        # Save to file
        save_markdown(markdown_content, output_file)
        
        print("Conversion completed successfully!")
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
