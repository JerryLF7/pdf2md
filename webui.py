"""
PDF to Markdown Web UI
Run: streamlit run webui.py
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# Auto-install dependencies if not available
def install_if_missing(package, import_name=None):
    if import_name is None:
        import_name = package
    try:
        __import__(import_name)
    except ImportError:
        print(f"Installing {package}...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_if_missing("streamlit")
install_if_missing("google-genai", "google.genai")
install_if_missing("python-dotenv", "dotenv")
install_if_missing("pymupdf", "fitz")

import io
import zipfile

import streamlit as st
import fitz
from pdf2md import convert_pdf_to_markdown, load_prompt


# Settings file path
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf2md_settings.json")


def load_settings():
    """Load settings from local file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_settings(settings):
    """Save settings to local file"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Failed to save settings: {e}")
        return False


def clear_settings():
    """Clear saved settings"""
    try:
        if os.path.exists(SETTINGS_FILE):
            os.remove(SETTINGS_FILE)
        return True
    except Exception:
        return False


def get_pdf_page_count(pdf_file) -> int:
    """Get page count of an uploaded PDF file"""
    try:
        # Save to temp and read
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.getvalue())
            tmp_path = tmp.name
        doc = fitz.open(tmp_path)
        page_count = len(doc)
        doc.close()
        os.unlink(tmp_path)
        return page_count
    except Exception:
        return 1  # Default to 1 page if can't read


st.set_page_config(page_title="PDF to Markdown Converter", page_icon="📄", layout="wide")

# Initialize session state for settings
if 'settings_loaded' not in st.session_state:
    saved_settings = load_settings()
    st.session_state.api_key = saved_settings.get("api_key", "")
    st.session_state.base_url = saved_settings.get("base_url", "https://generativelanguage.googleapis.com/")
    st.session_state.model = saved_settings.get("model", "gemini-3-flash-preview")
    st.session_state.chunk_size = saved_settings.get("chunk_size", 5)
    st.session_state.use_stream = saved_settings.get("use_stream", True)
    st.session_state.force_chunking = saved_settings.get("force_chunking", False)
    st.session_state.include_toc = saved_settings.get("include_toc", False)
    # Get available prompt files
    prompt_files = [f for f in os.listdir(os.path.dirname(__file__)) if f.startswith('prompt') and f.endswith('.md')] if os.path.exists(os.path.dirname(__file__)) else []
    default_prompt = saved_settings.get("prompt_option", prompt_files[0] if prompt_files else "prompt_general.md")
    st.session_state.prompt_option = default_prompt
    st.session_state.custom_prompt = saved_settings.get("custom_prompt", "")
    st.session_state.settings_loaded = True


# Initialize session state for persistent results
if 'converted_results' not in st.session_state:
    st.session_state.converted_results = []


# Header
st.title("📄 PDF to Markdown Converter")
st.markdown("Convert your PDF documents into clean Markdown using Gemini AI.")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Save/Load settings buttons
    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Save Settings", use_container_width=True):
            settings = {
                "api_key": st.session_state.api_key,
                "base_url": st.session_state.base_url,
                "model": st.session_state.model,
                "chunk_size": st.session_state.chunk_size,
                "use_stream": st.session_state.use_stream,
                "force_chunking": st.session_state.force_chunking,
                "include_toc": st.session_state.include_toc,
                "prompt_option": st.session_state.prompt_option,
                "custom_prompt": st.session_state.custom_prompt
            }
            if save_settings(settings):
                st.success("Settings saved! ✅")
    with col_clear:
        if st.button("🗑️ Clear Saved", use_container_width=True):
            if clear_settings():
                st.session_state.api_key = ""
                st.session_state.base_url = "https://generativelanguage.googleapis.com/"
                st.session_state.model = "gemini-3-flash-preview"
                st.session_state.chunk_size = 5
                st.session_state.use_stream = True
                st.session_state.force_chunking = False
                st.session_state.include_toc = False
                st.session_state.prompt_option = "prompt_general.md"
                st.session_state.custom_prompt = ""
                st.success("Settings cleared! ✅")
                st.rerun()
    
    st.divider()
    
    api_key = st.text_input("API Key", type="password", value=st.session_state.api_key, 
                           help="Gemini API Key", key="api_key_input")
    st.session_state.api_key = api_key
    
    base_url = st.text_input("Base URL (optional)", value=st.session_state.base_url, 
                            key="base_url_input")
    st.session_state.base_url = base_url
    
    model = st.text_input("Model", value=st.session_state.model, key="model_input")
    st.session_state.model = model
    
    with st.expander("Advanced Options"):
        chunk_size = st.number_input("Chunk Size (Pages)", min_value=1, max_value=20, 
                                     value=st.session_state.chunk_size, key="chunk_size_input")
        st.session_state.chunk_size = chunk_size
        
        use_stream = st.toggle("Stream Output", value=st.session_state.use_stream, 
                              key="use_stream_toggle")
        st.session_state.use_stream = use_stream
        
        force_chunking = st.toggle("Force Chunking", value=st.session_state.force_chunking,
                                   key="force_chunking_toggle")
        st.session_state.force_chunking = force_chunking
        
        include_toc = st.toggle("Include TOC", value=st.session_state.include_toc,
                                help="Include Table of Contents in output", key="include_toc_toggle")
        st.session_state.include_toc = include_toc
        
        # Prompt file selection
        prompt_files = [f for f in os.listdir(os.path.dirname(__file__)) if f.startswith('prompt') and f.endswith('.md')] if os.path.exists(os.path.dirname(__file__)) else []
        if not prompt_files:
            prompt_files = ["prompt_general.md"]
        
        try:
            prompt_index = prompt_files.index(st.session_state.prompt_option) if st.session_state.prompt_option in prompt_files else 0
        except:
            prompt_index = 0
            
        prompt_option = st.selectbox("Prompt Template", prompt_files, index=prompt_index, key="prompt_select")
        st.session_state.prompt_option = prompt_option
        
    custom_prompt = st.text_area("Custom Prompt (optional)", height=200, 
                                 value=st.session_state.custom_prompt,
                                 placeholder="Or enter custom prompt here...", key="custom_prompt_input")
    st.session_state.custom_prompt = custom_prompt

st.divider()

# Main Layout: Two Columns
col_input, col_output = st.columns(2, gap="large")

with col_input:
    st.subheader("📤 1. Upload & Convert")
    uploaded_files = st.file_uploader("Drop your PDF files here", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)} file(s) ready to convert:**")
        for f in uploaded_files:
            st.caption(f"📄 {f.name}")
            
        st.write("") # spacing
        
        if st.button("🚀 Start Conversion", type="primary", use_container_width=True):
            if not api_key:
                st.error("❌ Please enter your Gemini API Key in the sidebar.")
            else:
                # Determine which prompt to use
                if custom_prompt.strip():
                    prompt = custom_prompt
                elif prompt_option:
                    prompt = load_prompt(prompt_option, skip_toc=not include_toc)
                else:
                    prompt = load_prompt("prompt_general.md", skip_toc=not include_toc)
                
                # Pre-calculate total pages for accurate progress tracking
                file_page_counts = []
                total_pages = 0
                for f in uploaded_files:
                    page_count = get_pdf_page_count(f)
                    file_page_counts.append(page_count)
                    total_pages += page_count
                
                progress_container = st.container()
                progress_bar = progress_container.progress(0)
                status_text = progress_container.empty()
                
                for i, f in enumerate(uploaded_files):
                    file_pages = file_page_counts[i]
                    file_name = f.name  # Capture file name to avoid closure issues
                    
                    # Create progress callback for this file
                    def make_progress_callback(file_idx, file_pages_count, current_file_name):
                        def update_progress(chunk_num, total_chunks, page_start, page_end, file_total_pages):
                            # Calculate base progress from previously processed files
                            base_progress = sum(file_page_counts[:file_idx]) / total_pages
                            
                            if total_chunks > 1:
                                # Chunked file: progress = base + (current_chunk_progress / total_pages)
                                chunk_progress = chunk_num / total_chunks
                                current_file_progress = (chunk_progress * file_pages_count) / total_pages
                            else:
                                # Non-chunked file: progress = base + (file_pages / total_pages)
                                current_file_progress = file_pages_count / total_pages
                            
                            total_progress = min(base_progress + current_file_progress, 1.0)
                            progress_bar.progress(total_progress)
                            
                            if total_chunks > 1:
                                status_text.text(f"Processing {current_file_name}: Chunk {chunk_num}/{total_chunks} (pages {page_start+1}-{page_end+1})")
                            else:
                                status_text.text(f"Processing {current_file_name} ({file_pages_count} pages)")
                        return update_progress
                    
                    progress_callback = make_progress_callback(i, file_pages, file_name)
                    
                    # Save uploaded file to temp
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
                        tmp_input.write(f.getvalue())
                        tmp_input_path = tmp_input.name
                    
                    try:
                        output_md = convert_pdf_to_markdown(
                            pdf_path=tmp_input_path,
                            api_key=api_key,
                            prompt=prompt,
                            base_url=base_url if base_url.strip() else None,
                            model_name=model,
                            chunk_size=chunk_size,
                            stream=use_stream,
                            use_chunking=force_chunking,
                            progress_callback=progress_callback
                        )
                        
                        # Store in session state
                        st.session_state.converted_results.append({
                            "name": f.name,
                            "md": output_md,
                            "id": f.name + "_" + str(len(st.session_state.converted_results))
                        })
                    except Exception as e:
                        st.error(f"❌ Error converting {f.name}: {str(e)}")
                    finally:
                        if os.path.exists(tmp_input_path):
                            os.unlink(tmp_input_path)
                
                progress_bar.progress(1.0)
                status_text.success(f"✅ Successfully converted {len(uploaded_files)} file(s) ({total_pages} pages)!")
                st.balloons()

with col_output:
    st.subheader("📥 2. Converted Results")
    
    if st.session_state.converted_results:
        # Top action bar
        col_top1, col_top2, col_top3 = st.columns([1, 1, 1])
        
        # Create ZIP file for batch download
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for result in st.session_state.converted_results:
                output_filename = result['name'].replace(".pdf", ".md")
                zip_file.writestr(output_filename, result['md'])
        zip_buffer.seek(0)
        
        with col_top1:
            st.download_button(
                label="📦 Download All (ZIP)",
                data=zip_buffer,
                file_name="converted_files.zip",
                mime="application/zip",
                key="dl_all_zip",
                type="primary",
                use_container_width=True
            )
        with col_top3:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.converted_results = []
                st.rerun()
        
        st.divider()
        
        # Display results as cards
        for result in reversed(st.session_state.converted_results): # Show newest first
            output_filename = result['name'].replace(".pdf", ".md")
            
            # Card-style container
            with st.container(border=True):
                col_card1, col_card2 = st.columns([4, 1], vertical_alignment="center")
                with col_card1:
                    st.markdown(f"**📄 {result['name']}**")
                    st.caption(f"→ {output_filename}")
                with col_card2:
                    st.download_button(
                        label="📥",
                        data=result['md'],
                        file_name=output_filename,
                        mime="text/markdown",
                        key=f"dl_{result['id']}",
                        use_container_width=True
                    )
    else:
        st.info("💡 Converted files will appear here.")
