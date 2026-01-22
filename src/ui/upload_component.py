"""
PDF upload UI component with validation.
"""
import streamlit as st
from typing import Optional, Tuple
import tempfile
import os

import pdfplumber


def validate_pdf(file_bytes: bytes, max_pages: int = 20) -> Tuple[bool, str, int]:
    """
    Validate uploaded PDF file.
    
    Returns:
        Tuple of (is_valid, message, page_count)
    """
    try:
        # Save to temp file for pdfplumber
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        # Open and validate
        with pdfplumber.open(tmp_path) as pdf:
            page_count = len(pdf.pages)
            
            if page_count == 0:
                return False, "PDF has no pages", 0
            
            if page_count > max_pages:
                return False, f"PDF has {page_count} pages (max: {max_pages})", page_count
            
            return True, f"Valid PDF with {page_count} pages", page_count
    
    except Exception as e:
        return False, f"Invalid PDF file: {str(e)}", 0
    
    finally:
        # Cleanup temp file
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass


def render_upload(max_pages: int = 20) -> Optional[Tuple[bytes, str]]:
    """
    Render PDF upload component and return uploaded file.
    
    Returns:
        Tuple of (file_bytes, filename) or None if no valid file uploaded
    """
    st.subheader("📤 Upload Annual Report")
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help=f"Upload an annual report PDF (max {max_pages} pages)"
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        
        # Validate the PDF
        with st.spinner("Validating PDF..."):
            is_valid, message, page_count = validate_pdf(file_bytes, max_pages)
        
        if is_valid:
            st.success(f"✅ {message}")
            
            # Show file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Name", uploaded_file.name)
            with col2:
                st.metric("Pages", page_count)
            with col3:
                size_mb = len(file_bytes) / (1024 * 1024)
                st.metric("Size", f"{size_mb:.2f} MB")
            
            return file_bytes, uploaded_file.name
        else:
            st.error(f"❌ {message}")
            return None
    
    return None
