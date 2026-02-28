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
base_url = st.sidebar.text_input("Base URL (optional)", placeholder="https://api.example.com/v1")
model = st.sidebar.text_input("Model", value="gemini-2.0-flash-exp")
chunk_size = st.sidebar.number_input("Chunk Size", min_value=1, max_value=10, value=2)
use_stream = st.sidebar.toggle("Stream Output", value=True)
use_chunking = st.sidebar.toggle("Use Chunking", value=False)

# Prompt file selection
prompt_files = [f for f in os.listdir(os.path.dirname(__file__)) if f.startswith('prompt') and f.endswith('.md')]
prompt_file = st.sidebar.selectbox("Prompt Template", prompt_files if prompt_files else ["prompt_v4.md"])

# Main area
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    st.info(f"📎 {uploaded_file.name}")
    
    if st.button("🚀 Convert to Markdown"):
        if not api_key:
            st.error("❌ Please enter API Key")
        else:
            with st.spinner("Converting..."):
                # Save uploaded file to temp
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
                    tmp_input.write(uploaded_file.getvalue())
                    tmp_input_path = tmp_input.name
                
                try:
                    # Load prompt
                    prompt = load_prompt(prompt_file)
                    
                    # Convert
                    output_md = convert_pdf_to_markdown(
                        pdf_path=tmp_input_path,
                        api_key=api_key,
                        prompt=prompt,
                        base_url=base_url if base_url else None,
                        model_name=model,
                        chunk_size=chunk_size,
                        stream=use_stream,
                        use_chunking=use_chunking
                    )
                    
                    # Show result
                    st.success("✅ Done!")
                    st.text_area("Markdown Output", output_md, height=400)
                    
                    # Download button
                    output_filename = uploaded_file.name.replace(".pdf", ".md")
                    st.download_button(
                        label="📥 Download Markdown",
                        data=output_md,
                        file_name=output_filename,
                        mime="text/markdown"
                    )
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                finally:
                    os.unlink(tmp_input_path)
