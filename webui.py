"""
PDF to Markdown Web UI
Run: streamlit run webui.py
"""

# Auto-install streamlit if not available
try:
    import streamlit as st
except ImportError:
    print("Installing streamlit...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

import os
import sys
import tempfile

# Auto-install dependencies if not available
try:
    import google.genai as genai
except ImportError:
    print("Installing google-genai...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-genai"])
    import google.genai as genai

try:
    from dotenv import load_dotenv
except ImportError:
    print("Installing python-dotenv...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv

try:
    import fitz
except ImportError:
    print("Installing PyMuPDF...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

# Add current dir to path
sys.path.insert(0, os.path.dirname(__file__))

from pdf2md import convert_pdf_to_markdown, load_prompt

st.set_page_config(page_title="PDF to Markdown", page_icon="📄")

st.title("📄 PDF to Markdown Converter")

# Sidebar settings
st.sidebar.header("⚙️ Settings")

api_key = st.sidebar.text_input("API Key", type="password", help="Gemini API Key")
base_url = st.sidebar.text_input("Base URL (optional)", value="https://generativelanguage.googleapis.com/")
model = st.sidebar.text_input("Model", value="gemini-3-flash-preview")
chunk_size = st.sidebar.number_input("Chunk Size", min_value=1, max_value=10, value=2)
use_stream = st.sidebar.toggle("Stream Output", value=True)
force_chunking = st.sidebar.toggle("Force Chunking", value=False)

# Prompt file selection
prompt_files = [f for f in os.listdir(os.path.dirname(__file__)) if f.startswith('prompt') and f.endswith('.md')]
prompt_option = st.sidebar.selectbox("Prompt Template", prompt_files if prompt_files else ["prompt_v4.md"])

# Custom prompt input
custom_prompt = st.sidebar.text_area("Custom Prompt (optional)", height=150, placeholder="Or enter custom prompt here...")

# Main area
st.header("📁 Upload & Convert")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📤 Uploaded Files")
    uploaded_files = st.file_uploader("Upload PDF", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected:**")
        for f in uploaded_files:
            st.write(f"• {f.name}")

with col2:
    st.subheader("📥 Converted Results")
    
    if uploaded_files and st.button("🚀 Convert to Markdown", type="primary"):
        if not api_key:
            st.error("❌ Please enter API Key")
        else:
            # Determine which prompt to use
            if custom_prompt.strip():
                prompt = custom_prompt
            elif prompt_option:
                prompt = load_prompt(prompt_option)
            else:
                prompt = load_prompt("prompt_v4.md")
            
            results = []
            progress_bar = st.progress(0)
            
            for i, f in enumerate(uploaded_files):
                progress_bar.progress((i + 1) / len(uploaded_files))
                
                with st.spinner(f"Converting {f.name}..."):
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
                        results.append((f.name, output_md))
                    except Exception as e:
                        st.error(f"❌ Error: {f.name} - {str(e)}")
                    finally:
                        os.unlink(tmp_input_path)
            
            progress_bar.empty()
            
            if results:
                st.success(f"✅ {len(results)} file(s) converted!")
                
                for filename, md_content in results:
                    output_filename = filename.replace(".pdf", ".md")
                    st.download_button(
                        label=f"📥 {output_filename}",
                        data=md_content,
                        file_name=output_filename,
                        mime="text/markdown",
                        use_container_width=True
                    )
