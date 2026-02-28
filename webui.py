"""
PDF to Markdown Web UI
Run: streamlit run webui.py
"""

import sys
import os
import tempfile

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
from pdf2md import convert_pdf_to_markdown, load_prompt

st.set_page_config(page_title="PDF to Markdown Converter", page_icon="📄", layout="wide")

# Initialize session state for persistent results
if 'converted_results' not in st.session_state:
    st.session_state.converted_results = []

# Header
st.title("📄 PDF to Markdown Converter")
st.markdown("Convert your PDF documents into clean Markdown using Gemini AI.")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("API Key", type="password", help="Gemini API Key")
    base_url = st.text_input("Base URL (optional)", value="https://generativelanguage.googleapis.com/")
    model = st.text_input("Model", value="gemini-3-flash-preview")
    
    with st.expander("Advanced Options"):
        chunk_size = st.number_input("Chunk Size (Pages)", min_value=1, max_value=20, value=2)
        use_stream = st.toggle("Stream Output", value=True)
        force_chunking = st.toggle("Force Chunking", value=False)
        
        # Prompt file selection
        prompt_files = [f for f in os.listdir(os.path.dirname(__file__)) if f.startswith('prompt') and f.endswith('.md')]
        prompt_option = st.selectbox("Prompt Template", prompt_files if prompt_files else ["prompt_v4.md"])
        
    custom_prompt = st.text_area("Custom Prompt (optional)", height=200, placeholder="Or enter custom prompt here...")

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
                    prompt = load_prompt(prompt_option)
                else:
                    prompt = load_prompt("prompt_v4.md")
                
                progress_container = st.container()
                progress_bar = progress_container.progress(0)
                status_text = progress_container.empty()
                
                for i, f in enumerate(uploaded_files):
                    progress = (i + 1) / len(uploaded_files)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing ({i+1}/{len(uploaded_files)}): {f.name}...")
                    
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
                            use_chunking=force_chunking
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
                
                status_text.success(f"✅ Successfully converted {len(uploaded_files)} file(s)!")
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
