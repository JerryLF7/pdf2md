#!/usr/bin/env python3
"""
PDF to Markdown converter using Google Gemini API
Usage: python pdf2md.py <pdf_file>

Supports chunking for large PDFs (>100 pages) to handle token limits and 503 errors.
"""

import os
import sys
import base64
import argparse
import json
import re
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

# Try to import PyMuPDF (fitz), install if not available
try:
    import fitz
except ImportError:
    print("Installing PyMuPDF (fitz)...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

# Try to import tenacity, install if not available
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
except ImportError:
    print("Installing tenacity...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tenacity"])
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Load .env file
load_dotenv()

# Context character limit for chunking
CONTEXT_CHAR_LIMIT = 500


def load_prompt(prompt_file: str = "prompt_v4.md") -> str:
    """Load the prompt from prompt_v4.md file"""
    prompt_path = Path(prompt_file)
    if not prompt_path.exists():
        print(f"Warning: {prompt_file} not found, using default prompt")
        return "Convert the following PDF content to well-formatted Markdown:"
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def extract_pdf_pages(pdf_path: str) -> list:
    """Extract text from each page of the PDF using PyMuPDF
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of dictionaries with 'page_num' and 'text' keys
    """
    pages = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            # Clean up whitespace
            text = text.strip()
            if text:
                pages.append({
                    'page_num': page_num + 1,  # 1-based for display
                    'text': text
                })
        doc.close()
    except Exception as e:
        print(f"Error extracting PDF pages: {e}")
        raise
    return pages


def stitch_markdown_chunks(chunks: list) -> str:
    """Stitch together markdown chunks with proper handling of tables and sentences
    
    Args:
        chunks: List of markdown strings from each chunk
        
    Returns:
        Combined markdown string
    """
    if not chunks:
        return ""
    
    if len(chunks) == 1:
        return chunks[0]
    
    result = chunks[0]
    
    for i in range(1, len(chunks)):
        chunk = chunks[i]
        
        # Check if previous chunk ends with a table (no closing newline properly)
        # and current chunk might continue it
        prev_lines = result.rstrip().split('\n')
        curr_lines = chunk.lstrip().split('\n')
        
        # If previous chunk ends with table marker (|) and current has content
        if prev_lines and prev_lines[-1].strip().startswith('|'):
            # Check if current chunk starts with table continuation
            if curr_lines and ('|' in curr_lines[0] or curr_lines[0].strip().startswith('|')):
                # Ensure proper table continuation - add newline if needed
                if not result.rstrip().endswith('\n'):
                    result += '\n'
                elif result.rstrip().endswith('|'):
                    result += '\n'
        
        # Sentence merging: if previous doesn't end with sentence-ending punctuation
        # and current starts with lowercase, remove extra newline
        prev_trimmed = result.rstrip()
        curr_trimmed = chunk.lstrip()
        
        if prev_trimmed and curr_trimmed:
            prev_ends_punctuation = prev_trimmed[-1] in '.!?。！？'
            curr_starts_lowercase = curr_trimmed[0].islower() and curr_trimmed[0].isalpha()
            
            # Check if we should merge sentences (no new paragraph)
            if not prev_ends_punctuation and curr_starts_lowercase:
                # Remove the extra newline between chunks for sentence continuity
                result = result.rstrip()
                # Add a space if the last char is not whitespace
                if result and not result[-1].isspace():
                    result += ' '
                result += curr_trimmed
            else:
                # Normal paragraph separation
                result += '\n\n' + curr_trimmed
        else:
            result += '\n\n' + chunk
    
    return result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def convert_chunk_with_retry(client, model_name: str, pdf_path: str, page_start: int, page_end: int, 
                              prev_context: str, prompt_template: str, config) -> str:
    """Convert a single chunk of PDF pages with retry logic
    
    Args:
        client: Gemini client
        model_name: Model name
        pdf_path: Path to PDF file
        page_start: Starting page number (0-based)
        page_end: Ending page number (0-based, inclusive)
        prev_context: Previous chunk's output (last 500 chars)
        prompt_template: Prompt template with placeholders
        config: Generation config
        
    Returns:
        Markdown string for this chunk
    """
    from google.genai import types
    
    # Extract text for this chunk
    doc = fitz.open(pdf_path)
    chunk_text = ""
    for page_num in range(page_start, min(page_end + 1, len(doc))):
        page = doc[page_num]
        page_text = page.get_text("text").strip()
        if page_text:
            chunk_text += f"\n--- Page {page_num + 1} ---\n"
            chunk_text += page_text + "\n"
    doc.close()
    
    if not chunk_text:
        return ""
    
    # Prepare prompt with placeholders
    final_prompt = prompt_template.replace('{PREV_CONTEXT}', prev_context or "(No previous context - this is the first chunk)")
    final_prompt = final_prompt.replace('{PDF_CONTENT}', chunk_text)
    final_prompt = final_prompt.replace('{PREVIOUS_CONTEXT}', prev_context or "(No previous context - this is the first chunk)")
    final_prompt = final_prompt.replace('{CURRENT_PDF_CONTENT}', chunk_text)
    
    # Create PDF part for this chunk
    # For chunking, we read the PDF file and send specific pages
    # Since we're sending text, we'll use the text part only
    text_part = types.Part.from_text(text=final_prompt)
    
    # Also include PDF for better context if available
    pdf_part = None
    try:
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        # Only include the relevant pages - use a workaround by sending full PDF
        # The API will handle it, but for chunking we rely more on the text extraction
        pdf_part = types.Part.from_bytes(data=pdf_data, mime_type='application/pdf')
    except Exception as e:
        print(f"Warning: Could not load PDF for chunk: {e}")
    
    # Generate content
    contents = [text_part]
    if pdf_part:
        contents.insert(0, pdf_part)
    
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config
    )
    
    return response.text if response.text else ""


def encode_pdf_to_base64(pdf_path: str) -> str:
    """Encode PDF file to base64"""
    with open(pdf_path, 'rb') as pdf_file:
        return base64.b64encode(pdf_file.read()).decode('utf-8')


def get_output_filename(pdf_path: str) -> str:
    """Generate output markdown filename from PDF filename"""
    pdf_name = Path(pdf_path).stem
    return f"{pdf_name}.md"


def convert_pdf_to_markdown(pdf_path: str, api_key: str, prompt: str = None, base_url: str = None, 
                           model_name: str = None, stream: bool = True, chunk_size: int = 1,
                           use_chunking: bool = False) -> str:
    """Convert PDF to Markdown using Gemini API
    
    Args:
        pdf_path: Path to the PDF file
        api_key: Gemini API key
        prompt: Custom prompt text
        base_url: Custom base URL
        model_name: Model to use
        stream: Use streaming mode to avoid timeouts (default: True)
        chunk_size: Number of pages per chunk (default: 1)
        use_chunking: Enable chunking for large PDFs (default: False)
    """
    from google.genai import types
    
    # Default model
    if model_name is None:
        model_name = 'gemini-3-flash-preview'
    
    # Load prompt if not provided
    if prompt is None:
        prompt = load_prompt()
    
    # Configure client - always use Client, never use configure()
    if base_url:
        http_options = types.HttpOptions(baseUrl=base_url)
        client = genai.Client(api_key=api_key, http_options=http_options)
    else:
        client = genai.Client(api_key=api_key)
    
    # Determine config based on model
    if model_name.startswith('gemini-3'):
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH)
        )
    else:
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=1024)
        )
    
    # Check if we should use chunking
    # Auto-enable chunking for PDFs with more than 10 pages unless explicitly disabled
    if not use_chunking:
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            if page_count > 10:
                print(f"PDF has {page_count} pages, enabling chunking by default...")
                use_chunking = True
        except Exception:
            pass
    
    # Use chunking if enabled
    if use_chunking and chunk_size > 0:
        print(f"Using chunking mode with {chunk_size} page(s) per chunk...")
        return _convert_pdf_with_chunking(pdf_path, client, model_name, prompt, config, chunk_size)
    
    # Original single-shot conversion
    # Encode PDF
    pdf_data = encode_pdf_to_base64(pdf_path)
    
    # Create the prompt with PDF
    full_prompt = f"{prompt}\n\nPlease convert the following PDF to Markdown:"
    
    # Use types.Part to wrap the PDF content
    pdf_part = types.Part.from_bytes(
        data=base64.b64decode(pdf_data) if pdf_data else b'',
        mime_type='application/pdf'
    )
    text_part = types.Part.from_text(text=full_prompt)
    
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


def _convert_pdf_with_chunking(pdf_path: str, client, model_name: str, prompt_template: str, 
                               config, chunk_size: int = 1) -> str:
    """Internal function to convert PDF using chunking
    
    Args:
        pdf_path: Path to the PDF file
        client: Gemini client
        model_name: Model name
        prompt_template: Prompt template with placeholders
        config: Generation config
        chunk_size: Number of pages per chunk
        
    Returns:
        Combined markdown string
    """
    from google.genai import types
    
    # Get total page count
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    print(f"Processing {total_pages} pages in chunks of {chunk_size}...")
    
    chunks = []
    prev_context = ""
    
    # Process in chunks
    for start_page in range(0, total_pages, chunk_size):
        end_page = min(start_page + chunk_size - 1, total_pages - 1)
        chunk_num = start_page // chunk_size + 1
        total_chunks = (total_pages + chunk_size - 1) // chunk_size
        
        print(f"Processing chunk {chunk_num}/{total_chunks} (pages {start_page + 1}-{end_page + 1})...")
        
        try:
            chunk_text = convert_chunk_with_retry(
                client=client,
                model_name=model_name,
                pdf_path=pdf_path,
                page_start=start_page,
                page_end=end_page,
                prev_context=prev_context,
                prompt_template=prompt_template,
                config=config
            )
            
            if chunk_text:
                chunks.append(chunk_text)
                # Update context for next chunk (last 500 chars)
                prev_context = chunk_text[-CONTEXT_CHAR_LIMIT:] if len(chunk_text) > CONTEXT_CHAR_LIMIT else chunk_text
            else:
                print(f"Warning: Empty result for chunk {chunk_num}")
                
        except Exception as e:
            print(f"Error processing chunk {chunk_num}: {e}")
            # Continue with next chunk instead of failing completely
            continue
    
    if not chunks:
        print("Warning: No chunks were successfully processed")
        return ""
    
    # Stitch chunks together
    print("Stitching chunks together...")
    result = stitch_markdown_chunks(chunks)
    
    print(f"Conversion completed! Total chunks: {len(chunks)}")
    return result


def save_markdown(content: str, output_path: str):
    """Save markdown content to file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Markdown saved to: {output_path}")


def process_single_pdf(pdf_path: str, api_key: str, prompt: str, base_url: str, model_name: str, 
                      output_dir: str = None, stream: bool = True, chunk_size: int = 1, use_chunking: bool = None):
    """Process a single PDF file
    
    Args:
        pdf_path: Path to the PDF file
        api_key: Gemini API key
        prompt: Prompt template
        base_url: Custom base URL
        model_name: Model name
        output_dir: Output directory
        stream: Use streaming mode
        chunk_size: Number of pages per chunk
        use_chunking: Enable chunking (None for auto)
    """
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
        markdown_content = convert_pdf_to_markdown(
            pdf_path, api_key, prompt, base_url, model_name, 
            stream=stream, chunk_size=chunk_size, use_chunking=use_chunking
        )
        
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
    parser.add_argument('-p', '--prompt', help='Custom prompt file (default: prompt_v4.md)')
    parser.add_argument('-u', '--base-url', help='Custom base URL for Gemini API (optional, will use BASE_URL env var if not provided)')
    parser.add_argument('-m', '--model', help='Gemini model to use (default: gemini-3-flash-preview)', default='gemini-3-flash-preview')
    parser.add_argument('-d', '--directory', '--dir', action='store_true', help='Treat input as a directory and process all PDFs in it')
    parser.add_argument('-s', '--stream', action='store_true', default=True, help='Use streaming mode to avoid timeouts (default: enabled)')
    parser.add_argument('--no-stream', dest='stream', action='store_false', help='Disable streaming mode')
    parser.add_argument('-c', '--chunk-size', type=int, default=2, help='Number of pages per chunk for large PDFs (default: 2, use 1 for more granular processing)')
    parser.add_argument('--no-chunking', dest='use_chunking', action='store_false', help='Disable automatic chunking for large PDFs')
    parser.add_argument('--force-chunking', dest='use_chunking', action='store_true', help='Force chunking for all PDFs')
    
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
    prompt_file = args.prompt if args.prompt else "prompt_v4.md"
    prompt = load_prompt(prompt_file)
    
    # Get stream option
    stream_mode = args.stream
    
    # Get chunking options
    chunk_size = args.chunk_size
    use_chunking = args.use_chunking  # None = auto, True = force, False = disable
    
    print(f"Chunk size: {chunk_size} page(s) per chunk")
    if use_chunking is None:
        print("Chunking: Auto (enabled for PDFs > 10 pages)")
    elif use_chunking:
        print("Chunking: Force enabled")
    else:
        print("Chunking: Disabled")
    
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
                if process_single_pdf(pdf_path, api_key, prompt, base_url, model_name, output_dir, 
                                     stream=stream_mode, chunk_size=chunk_size, use_chunking=use_chunking):
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
            markdown_content = convert_pdf_to_markdown(
                input_path, api_key, prompt, base_url, model_name, 
                stream=stream_mode, chunk_size=chunk_size, use_chunking=use_chunking
            )
            
            # Save to file
            save_markdown(markdown_content, output_file)
            
            print("Conversion completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
