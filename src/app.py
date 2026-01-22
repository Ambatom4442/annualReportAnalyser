"""
Main Streamlit application entry point with RAG-powered document analysis.
"""
import os
import warnings

# Suppress noisy warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", message=".*hf_xet.*")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

import streamlit as st
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime

from ui.upload_component import render_upload
from ui.dynamic_parameter_ui import render_dynamic_parameter_ui
from ui.preview_component import render_preview, render_export_panel
from ui.chat_component import render_chat_interface, render_document_library
from ui.floating_chat import (
    init_floating_chat_state, 
    render_floating_chat_panel,
    get_chat_agent
)
from extractors.text_extractor import TextExtractor
from extractors.table_extractor import TableExtractor
from extractors.image_extractor import ImageExtractor
from extractors.metadata_extractor import MetadataExtractor
from agents.comment_agent import CommentGeneratorAgent
from agents.document_analyzer import DocumentAnalyzerAgent
from agents.chart_analyzer import ChartAnalyzer
from models.extracted_data import (
    ExtractedData, 
    PerformanceData, 
    HoldingData, 
    SectorData,
    TableData
)
from config import config

# Initialize storage layers (lazy loading)
_document_store = None
_vector_store = None
_embedding_service = None
_secondary_store = None
_secondary_processor = None


def get_document_store():
    """Get or create the document store."""
    global _document_store
    if _document_store is None:
        try:
            from storage.document_store import DocumentStore
            data_dir = Path(config.DATA_DIR) if hasattr(config, 'DATA_DIR') else Path(".data")
            _document_store = DocumentStore(data_dir)
        except Exception as e:
            st.warning(f"Could not initialize document store: {e}")
            return None
    return _document_store


def get_embedding_service():
    """Get or create the embedding service."""
    global _embedding_service
    if _embedding_service is None:
        try:
            from storage.embedding_service import EmbeddingService
            _embedding_service = EmbeddingService(api_key=config.GEMINI_API_KEY)
        except Exception as e:
            st.warning(f"Could not initialize embedding service: {e}")
            return None
    return _embedding_service


def get_vector_store():
    """Get or create the vector store."""
    global _vector_store
    if _vector_store is None:
        try:
            from storage.vector_store import VectorStore
            data_dir = Path(config.DATA_DIR) if hasattr(config, 'DATA_DIR') else Path(".data")
            _vector_store = VectorStore(
                api_key=config.GEMINI_API_KEY,
                persist_directory=str(data_dir / "chromadb")
            )
        except Exception as e:
            st.warning(f"Could not initialize vector store: {e}")
            return None
    return _vector_store


def get_secondary_store():
    """Get or create the secondary source store."""
    global _secondary_store
    if _secondary_store is None:
        try:
            from storage.secondary_store import SecondarySourceStore
            data_dir = Path(config.DATA_DIR) if hasattr(config, 'DATA_DIR') else Path(".data")
            _secondary_store = SecondarySourceStore(str(data_dir / "secondary_sources.db"))
        except Exception as e:
            st.warning(f"Could not initialize secondary store: {e}")
            return None
    return _secondary_store


def get_secondary_processor():
    """Get or create the secondary source processor."""
    global _secondary_processor
    if _secondary_processor is None:
        try:
            from processing.secondary_processor import SecondarySourceProcessor
            _secondary_processor = SecondarySourceProcessor(
                vector_store=get_vector_store(),
                secondary_store=get_secondary_store()
            )
        except Exception as e:
            st.warning(f"Could not initialize secondary processor: {e}")
            return None
    return _secondary_processor


def store_document(pdf_bytes: bytes, filename: str, extracted_data: ExtractedData, analysis: dict) -> Optional[str]:
    """Store document in persistent storage and vector DB with hybrid chunking."""
    doc_store = get_document_store()
    vec_store = get_vector_store()
    
    if not doc_store:
        return None
    
    try:
        # Store in document store (SQLite) using add_document API
        doc_id, is_new = doc_store.add_document(
            filename=filename,
            file_bytes=pdf_bytes,
            metadata={
                "fund_name": extracted_data.fund_name,
                "report_period": extracted_data.report_period,
                "uploaded_at": datetime.now().isoformat()
            }
        )
        
        # Update document metadata
        doc_store.update_document_metadata(
            doc_id=doc_id,
            fund_name=extracted_data.fund_name,
            report_period=extracted_data.report_period,
            benchmark=extracted_data.benchmark_index,
            currency=extracted_data.currency
        )
        
        # Save analysis cache - convert to JSON-serializable format
        def to_serializable(obj):
            """Convert object to JSON-serializable format."""
            # Skip internal attributes like _docling_result
            if hasattr(obj, '__dict__'):
                return {k: to_serializable(v) for k, v in obj.__dict__.items() 
                        if not k.startswith('_')}
            elif isinstance(obj, list):
                return [to_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: to_serializable(v) for k, v in obj.items()
                        if not k.startswith('_')}
            else:
                return obj
        
        doc_store.save_analysis(
            doc_id=doc_id,
            document_analysis=analysis,
            extracted_data=to_serializable(extracted_data) if extracted_data else {}
        )
        
        # Store embeddings in vector store using hybrid chunking
        if vec_store and extracted_data.raw_text:
            from processing.chunking import HybridDocumentChunker, DocumentChunker
            
            # Check if we have a Docling document for hybrid chunking
            docling_result = getattr(extracted_data, '_docling_result', None)
            
            if docling_result and docling_result.get("_docling_document"):
                # Use HybridChunker with Docling document
                chunker = HybridDocumentChunker(max_tokens=512)
                chunk_data = chunker.chunk_docling_document(
                    docling_result["_docling_document"],
                    include_metadata=True
                )
                chunks = [c["content"] for c in chunk_data]
                chunk_type = "hybrid"
            else:
                # Fallback to text-based chunking (smaller chunks for token safety)
                chunker = DocumentChunker()
                chunks = chunker.chunk_text(extracted_data.raw_text, chunk_size=500, overlap=100)
                chunk_type = "text"
            
            if chunks:
                # Delete existing chunks first (in case of re-upload)
                try:
                    vec_store.delete_document(doc_id)
                except:
                    pass  # May not exist yet
                
                vec_store.add_document(
                    doc_id=doc_id,
                    chunks=chunks,
                    metadatas=[{
                        "filename": filename or "",
                        "fund_name": (extracted_data.fund_name or "") if extracted_data.fund_name else "",
                        "chunk_index": i,
                        "chunk_type": chunk_type
                    } for i in range(len(chunks))]
                )
                st.toast(f"✅ Indexed {len(chunks)} {chunk_type} chunks for search")
            else:
                st.warning("No text chunks generated from document")
        
        return doc_id
    except Exception as e:
        st.error(f"Error storing document: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None


def load_stored_documents():
    """Load list of stored documents."""
    doc_store = get_document_store()
    if not doc_store:
        return []
    
    try:
        return doc_store.list_documents()
    except Exception:
        return []


def _dict_to_extracted_data(data: dict) -> ExtractedData:
    """Convert a dictionary back to ExtractedData object."""
    if not data:
        return ExtractedData()
    
    return ExtractedData(
        raw_text=data.get("raw_text", ""),
        fund_name=data.get("fund_name"),
        report_period=data.get("report_period"),
        benchmark_index=data.get("benchmark_index"),
        currency=data.get("currency"),
        performance=data.get("performance"),
        top_holdings=data.get("top_holdings"),
        sector_allocation=data.get("sector_allocation"),
        tables=data.get("tables", []),
        charts=data.get("charts", []),
        images=data.get("images", []),
        metadata=data.get("metadata", {})
    )


def delete_document(doc_id: str):
    """Delete a document and all associated secondary sources from storage."""
    doc_store = get_document_store()
    vec_store = get_vector_store()
    secondary_store = get_secondary_store()
    
    # Delete associated secondary sources first
    if secondary_store:
        try:
            count, source_ids = secondary_store.delete_by_parent_doc(doc_id)
            if count > 0:
                # Also delete secondary source chunks from vector store
                if vec_store:
                    for source_id in source_ids:
                        try:
                            # Delete chunks by source_id metadata
                            results = vec_store.collection.get(
                                where={"source_id": source_id},
                                include=[]
                            )
                            if results["ids"]:
                                vec_store.collection.delete(ids=results["ids"])
                        except Exception:
                            pass
                print(f"Deleted {count} secondary source(s) for document {doc_id}")
        except Exception as e:
            print(f"Error deleting secondary sources: {e}")
    
    if doc_store:
        try:
            doc_store.delete_document(doc_id)
        except Exception as e:
            st.error(f"Error deleting from document store: {e}")
    
    if vec_store:
        try:
            # Delete all chunks for this document
            vec_store.delete_document(doc_id)
        except Exception:
            pass  # Vector store might not have this document


def reindex_document(doc_id: str):
    """Re-index a single document into the vector store using hybrid chunking."""
    doc_store = get_document_store()
    vec_store = get_vector_store()
    
    if not doc_store or not vec_store:
        st.error("Storage not available")
        return
    
    try:
        # Get document info
        doc = doc_store.get_document(doc_id)
        if not doc:
            st.error(f"Document {doc_id} not found")
            return
        
        # Get cached analysis
        analysis = doc_store.get_analysis(doc_id)
        extracted_text = ""
        extracted_data = None
        
        if analysis and analysis.get("extracted_data"):
            extracted_text = analysis["extracted_data"].get("raw_text", "")
        
        # If no cached text, re-extract from PDF (which will use Docling if available)
        if not extracted_text:
            file_path = doc.get("file_path")
            if file_path:
                from pathlib import Path
                # Handle relative paths - they're relative to src/ directory
                pdf_path = Path(file_path)
                if not pdf_path.is_absolute():
                    # Try relative to current working directory
                    if not pdf_path.exists():
                        # Try relative to data directory
                        data_dir = Path(config.DATA_DIR) if hasattr(config, 'DATA_DIR') else Path(".data")
                        pdf_path = data_dir / "files" / f"{doc_id}.pdf"
                
                st.info(f"Reading PDF from: {pdf_path}")
                if pdf_path.exists():
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    extracted_data = _extract_pdf_data(pdf_bytes)
                    extracted_text = extracted_data.raw_text or ""
                else:
                    st.error(f"PDF file not found at: {pdf_path}")
                    return
        
        if not extracted_text:
            st.warning(f"No text found for document {doc_id}")
            return
        
        # Delete existing chunks
        try:
            vec_store.delete_document(doc_id)
        except:
            pass
        
        # Chunk and index using hybrid chunking if available
        from processing.chunking import HybridDocumentChunker, DocumentChunker
        
        # Check if we have a Docling document for hybrid chunking
        docling_result = getattr(extracted_data, '_docling_result', None) if extracted_data else None
        
        if docling_result and docling_result.get("_docling_document"):
            # Use HybridChunker with Docling document
            chunker = HybridDocumentChunker(max_tokens=512)
            chunk_data = chunker.chunk_docling_document(
                docling_result["_docling_document"],
                include_metadata=True
            )
            chunks = [c["content"] for c in chunk_data]
            chunk_type = "hybrid"
        else:
            # Fallback to text-based chunking
            chunker = DocumentChunker()
            chunks = chunker.chunk_text(extracted_text, chunk_size=1000, overlap=200)
            chunk_type = "text"
        
        if chunks:
            vec_store.add_document(
                doc_id=doc_id,
                chunks=chunks,
                metadatas=[{
                    "filename": doc.get("filename") or "",
                    "fund_name": doc.get("fund_name") or "",
                    "chunk_index": i,
                    "chunk_type": chunk_type
                } for i in range(len(chunks))]
            )
            st.success(f"✅ Indexed {len(chunks)} {chunk_type} chunks for {doc.get('filename') or doc_id}")
        else:
            st.warning(f"No chunks generated for {doc_id}")
            
    except Exception as e:
        st.error(f"Error re-indexing document: {e}")
        import traceback
        st.code(traceback.format_exc())


def reindex_all_documents():
    """Re-index all documents into the vector store."""
    stored_docs = load_stored_documents()
    
    if not stored_docs:
        st.info("No documents to re-index")
        return
    
    progress = st.progress(0)
    status = st.empty()
    
    for i, doc in enumerate(stored_docs):
        status.text(f"Re-indexing {doc.get('filename', doc['id'])}...")
        reindex_document(doc['id'])
        progress.progress((i + 1) / len(stored_docs))
    
    status.text("✅ Re-indexing complete!")
    progress.progress(1.0)


def main():
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Annual Report Analyser")
    st.markdown("*AI-powered tool for generating asset manager comments with persistent storage*")
    
    # Check API key
    if not config.GEMINI_API_KEY:
        st.error("⚠️ GEMINI_API_KEY not found. Please set it in your .env file.")
        st.stop()
    
    # Initialize session state
    if "pdf_data" not in st.session_state:
        st.session_state.pdf_data = None
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = None
    if "document_analysis" not in st.session_state:
        st.session_state.document_analysis = None
    if "analyzed_charts" not in st.session_state:
        st.session_state.analyzed_charts = None
    if "generated_comment" not in st.session_state:
        st.session_state.generated_comment = None
    if "comment_params" not in st.session_state:
        st.session_state.comment_params = None
    if "content_selections" not in st.session_state:
        st.session_state.content_selections = None
    if "current_doc_id" not in st.session_state:
        st.session_state.current_doc_id = None
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "generate"  # "generate" or "chat" or "library"
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🧭 Navigation")
        
        # Mode selection
        mode = st.radio(
            "Mode",
            ["📝 Generate Comment", "💬 Chat with Documents", "📚 Document Library"],
            index=["generate", "chat", "library"].index(st.session_state.app_mode) if st.session_state.app_mode in ["generate", "chat", "library"] else 0
        )
        
        if mode == "📝 Generate Comment":
            st.session_state.app_mode = "generate"
        elif mode == "💬 Chat with Documents":
            st.session_state.app_mode = "chat"
        else:
            st.session_state.app_mode = "library"
        
        st.divider()
        
        # Show progress for generate mode
        if st.session_state.app_mode == "generate":
            st.header("📑 Progress")
            
            step = 1
            if st.session_state.pdf_data:
                step = 2
            if st.session_state.document_analysis:
                step = 3
            if st.session_state.generated_comment:
                step = 4
                
            st.progress(step / 4)
            st.caption(f"Step {step} of 4")
            
            steps = [
                ("1️⃣", "Upload PDF", step >= 1),
                ("2️⃣", "AI Analysis", step >= 2),
                ("3️⃣", "Select Content", step >= 3),
                ("4️⃣", "Generate", step >= 4),
            ]
            
            for icon, label, done in steps:
                if done:
                    st.success(f"{icon} {label}")
                else:
                    st.info(f"{icon} {label}")
            
            st.divider()
            
            if st.button("🔄 Start Over", use_container_width=True):
                st.session_state.pdf_data = None
                st.session_state.extracted_data = None
                st.session_state.document_analysis = None
                st.session_state.analyzed_charts = None
                st.session_state.generated_comment = None
                st.session_state.comment_params = None
                st.session_state.content_selections = None
                st.session_state.current_doc_id = None
                st.rerun()
        
        # Show stored documents count
        stored_docs = load_stored_documents()
        st.divider()
        st.metric("📚 Stored Documents", len(stored_docs))
    
    # Main content area based on mode
    st.divider()
    
    if st.session_state.app_mode == "library":
        render_library_view()
    elif st.session_state.app_mode == "chat":
        render_chat_view()
    else:
        render_generate_view()


def render_library_view():
    """Render the document library view."""
    st.header("📚 Document Library")
    
    stored_docs = load_stored_documents()
    
    if not stored_docs:
        st.info("No documents stored yet. Upload a PDF in 'Generate Comment' mode to add documents to your library.")
        return
    
    st.markdown(f"**{len(stored_docs)} documents stored**")
    
    # Re-index button for fixing vector store
    if st.button("🔄 Re-index All Documents", help="Re-process documents into vector database for search"):
        reindex_all_documents()
        st.rerun()
    
    for doc in stored_docs:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{doc.get('filename', 'Unknown')}**")
                if doc.get('fund_name'):
                    st.caption(f"Fund: {doc['fund_name']}")
                upload_date = doc.get('upload_date') or doc.get('created_at')
                if upload_date:
                    st.caption(f"Uploaded: {upload_date[:10]}")
            
            with col2:
                if st.button("📝 Analyze", key=f"analyze_{doc['id']}", help="Generate comment for this document"):
                    # Load saved analysis and switch to generate mode
                    doc_store = get_document_store()
                    analysis = doc_store.get_analysis(doc['id']) if doc_store else None
                    
                    if analysis and analysis.get('document_analysis'):
                        # Load saved state
                        st.session_state.current_doc_id = doc['id']
                        st.session_state.document_analysis = analysis.get('document_analysis', {})
                        st.session_state.extracted_data = _dict_to_extracted_data(analysis.get('extracted_data', {}))
                        st.session_state.analyzed_charts = analysis.get('chart_analysis', [])
                        st.session_state.pdf_data = True  # Mark as loaded
                        st.session_state.generated_comment = None  # Reset to show Step 3
                        st.session_state.app_mode = "generate"
                        st.rerun()
                    else:
                        st.error(f"No saved analysis for this document. Please re-upload it.")
            
            with col3:
                if st.button("💬 Chat", key=f"chat_{doc['id']}"):
                    st.session_state.current_doc_id = doc['id']
                    st.session_state.app_mode = "chat"
                    st.rerun()
            
            with col4:
                if st.button("🔄 Index", key=f"idx_{doc['id']}", help="Re-index this document"):
                    reindex_document(doc['id'])
                    st.rerun()
            
            with col5:
                if st.button("🗑️ Delete", key=f"del_{doc['id']}"):
                    delete_document(doc['id'])
                    st.rerun()


def render_chat_view():
    """Render the chat interface view."""
    st.header("💬 Chat with Documents")
    
    # Get storage layers
    doc_store = get_document_store()
    vec_store = get_vector_store()
    
    if not vec_store:
        st.warning("Vector store not available. Chat functionality requires ChromaDB.")
        return
    
    # Create agent with tools - PERSIST in session state for memory to work
    if "chat_agent" not in st.session_state:
        st.session_state.chat_agent = CommentGeneratorAgent(
            api_key=config.GEMINI_API_KEY,
            model_name=config.GEMINI_MODEL,
            provider="gemini",
            vector_store=vec_store,
            document_store=doc_store
        )
    agent = st.session_state.chat_agent
    
    # Document selector
    stored_docs = load_stored_documents()
    if stored_docs:
        doc_options = {doc['filename']: doc['id'] for doc in stored_docs}
        doc_options["All Documents"] = None
        
        selected_doc = st.selectbox(
            "Select document context",
            options=list(doc_options.keys()),
            index=0
        )
        current_doc_id = doc_options[selected_doc]
    else:
        st.info("No documents in library. Upload documents first to chat with them.")
        current_doc_id = None
    
    # Render chat interface with secondary source support
    render_chat_interface(
        agent, 
        current_doc_id,
        secondary_processor=get_secondary_processor(),
        secondary_store=get_secondary_store()
    )


def render_generate_view():
    """Render the comment generation view with floating chat sidebar."""
    from ui.floating_chat import inject_floating_chat_css
    
    # Initialize floating chat state
    init_floating_chat_state()
    
    # Determine if we should show the chat panel (only after document is uploaded)
    show_chat_option = st.session_state.pdf_data is not None
    current_doc_id = st.session_state.get("current_doc_id")
    
    # Get document name safely (pdf_data can be dict or True when loaded from library)
    if isinstance(st.session_state.pdf_data, dict):
        document_name = st.session_state.pdf_data.get("filename", "Document")
    elif st.session_state.extracted_data and st.session_state.extracted_data.fund_name:
        document_name = st.session_state.extracted_data.fund_name
    else:
        document_name = "Document"
    
    # Inject CSS for floating chat
    is_chat_open = st.session_state.get("floating_chat_open", False)
    inject_floating_chat_css(is_chat_open)
    
    # Create layout: main content (60%) + chat sidebar (40%) when open
    if show_chat_option and is_chat_open:
        # 60:40 split when chat is open
        main_col, chat_col = st.columns([3, 2])
    else:
        main_col = st.container()
        chat_col = None
    
    # Main content area
    with main_col:
        # Chat toggle button (only show after document upload)
        if show_chat_option:
            toggle_col1, toggle_col2 = st.columns([10, 1])
            with toggle_col2:
                chat_icon = "💬" if not is_chat_open else "✕"
                chat_tooltip = "Open Chat" if not is_chat_open else "Close Chat"
                if st.button(chat_icon, key="toggle_chat_btn", help=chat_tooltip, use_container_width=True):
                    st.session_state.floating_chat_open = not is_chat_open
                    st.rerun()
        
        # Step 1: PDF Upload
        if st.session_state.pdf_data is None:
            st.header("📤 Step 1: Upload PDF")
            upload_result = render_upload(max_pages=config.MAX_PDF_PAGES)
            
            if upload_result is not None:
                file_bytes, filename = upload_result
                st.session_state.pdf_data = {
                    "bytes": file_bytes,
                    "filename": filename
                }
                st.rerun()
        
        # Step 2: AI Document Analysis
        elif st.session_state.document_analysis is None:
            st.header("🤖 Step 2: AI Document Analysis")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("📄 Extracting text from PDF...")
            progress_bar.progress(10)
            extracted_data = _extract_pdf_data(st.session_state.pdf_data["bytes"])
            st.session_state.extracted_data = extracted_data
            
            status_text.text("🔍 AI analyzing document structure...")
            progress_bar.progress(40)
            
            # Run document analyzer agent
            analyzer = DocumentAnalyzerAgent(
                api_key=config.GEMINI_API_KEY,
                model_name=config.GEMINI_MODEL
            )
            
            # Convert tables for analyzer
            tables_for_analysis = []
            for table in extracted_data.raw_tables:
                tables_for_analysis.append({
                    "page": table.page,
                    "headers": table.headers,
                    "rows": table.rows,
                    "type": table.table_type
                })
            
            document_analysis = analyzer.analyze_document(
                raw_text=extracted_data.raw_text or "",
                tables_data=tables_for_analysis
            )
            
            status_text.text("📊 Analyzing charts with AI Vision...")
            progress_bar.progress(70)
            
            # Analyze charts with vision
            image_extractor = ImageExtractor()
            chart_images = image_extractor.extract_charts_only(st.session_state.pdf_data["bytes"])
            
            analyzed_charts = []
            if chart_images:
                fund_context = f"Fund: {document_analysis.get('fund_info', {}).get('name', 'Unknown')}"
                analyzed_charts = analyzer.analyze_charts_with_vision(chart_images, fund_context)
            
            # Store document persistently
            status_text.text("💾 Storing document...")
            progress_bar.progress(90)
            
            doc_id = store_document(
                pdf_bytes=st.session_state.pdf_data["bytes"],
                filename=st.session_state.pdf_data["filename"],
                extracted_data=extracted_data,
                analysis=document_analysis
            )
            if doc_id:
                st.session_state.current_doc_id = doc_id
            
            progress_bar.progress(100)
            status_text.text("✅ Analysis complete!")
            
            st.session_state.document_analysis = document_analysis
            st.session_state.analyzed_charts = analyzed_charts
            
            st.success("✅ AI analysis complete! Document stored in library.")
            st.rerun()
        
        # Step 3: Configure with Dynamic UI
        elif st.session_state.generated_comment is None:
            st.header("🎛️ Step 3: Select Content & Configure")
            
            # Load saved selections if available
            doc_store = get_document_store()
            saved_selections = None
            current_doc_id = st.session_state.get("current_doc_id")
            
            if current_doc_id and doc_store:
                saved_selections = doc_store.get_user_selections(current_doc_id)
            
            # Render dynamic parameter UI based on AI analysis
            result = render_dynamic_parameter_ui(
                document_analysis=st.session_state.document_analysis,
                analyzed_charts=st.session_state.analyzed_charts or [],
                saved_selections=saved_selections,
                doc_id=current_doc_id,
                document_store=doc_store
            )
            
            if result is not None:
                params, content_selections = result
                st.session_state.comment_params = params
                st.session_state.content_selections = content_selections
                
                with st.spinner("🤖 Generating comment with AI..."):
                    try:
                        # Get storage layers
                        doc_store = get_document_store()
                        vec_store = get_vector_store()
                        
                        agent = CommentGeneratorAgent(
                            api_key=config.GEMINI_API_KEY,
                            model_name=config.GEMINI_MODEL,
                            provider="gemini",
                            vector_store=vec_store,
                            document_store=doc_store
                        )
                        
                        # Build context from selections
                        context = _build_context_from_selections(
                            st.session_state.document_analysis,
                            content_selections,
                            st.session_state.analyzed_charts or []
                        )
                        
                        comment = agent.generate(
                            st.session_state.extracted_data,
                            params,
                            additional_context=context
                        )
                        st.session_state.generated_comment = comment
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error generating comment: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        
        # Step 4: Preview and Export
        else:
            st.header("✨ Step 4: Review & Export")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                def on_regenerate():
                    st.session_state.generated_comment = None
                    st.rerun()
                
                edited_comment = render_preview(
                    st.session_state.generated_comment,
                    on_regenerate=on_regenerate,
                    comment_type=st.session_state.comment_params.comment_type if st.session_state.comment_params else "asset_manager_comment"
                )
                
                if edited_comment != st.session_state.generated_comment:
                    st.session_state.generated_comment = edited_comment
            
            with col2:
                render_export_panel(st.session_state.generated_comment)
    
    # Chat sidebar (only when open and document is available) - 40% width
    if chat_col is not None and show_chat_option:
        with chat_col:
            # Styled header
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <h3 style="margin: 0; color: white;">💬 Quick Chat</h3>
                <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">
                    📄 {}</p>
            </div>
            """.format(document_name), unsafe_allow_html=True)
            
            # Secondary Sources Management
            if current_doc_id:
                try:
                    from ui.attachment_component import render_manage_sources_modal
                    secondary_store = get_secondary_store()
                    secondary_processor = get_secondary_processor()
                    render_manage_sources_modal(
                        parent_doc_id=current_doc_id,
                        secondary_store=secondary_store,
                        processor=secondary_processor
                    )
                except ImportError:
                    pass
            
            # Get or create chat agent
            vec_store = get_vector_store()
            doc_store = get_document_store()
            agent = get_chat_agent(config, vec_store, doc_store)
            
            # Chat messages container - taller for 40% width
            chat_container = st.container(height=500)
            
            with chat_container:
                if not st.session_state.floating_chat_messages:
                    st.info("💡 Ask questions about the document while working on your comment!")
                else:
                    for msg in st.session_state.floating_chat_messages:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])
            
            # Chat input
            if prompt := st.chat_input("Ask about document...", key="floating_chat_input"):
                # Add user message
                st.session_state.floating_chat_messages.append({
                    "role": "user",
                    "content": prompt
                })
                
                # Get agent response
                with st.spinner("Thinking..."):
                    try:
                        response = agent.chat(prompt, doc_id=current_doc_id)
                        st.session_state.floating_chat_messages.append({
                            "role": "assistant",
                            "content": response
                        })
                    except Exception as e:
                        error_msg = f"Error: {str(e)}"
                        st.session_state.floating_chat_messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                st.rerun()
            
            # Clear chat button
            if st.session_state.floating_chat_messages:
                if st.button("🗑️ Clear Chat", key="clear_floating_chat", use_container_width=True):
                    st.session_state.floating_chat_messages = []
                    if hasattr(agent, 'clear_memory'):
                        agent.clear_memory()
                    st.rerun()


def _build_context_from_selections(
    document_analysis: dict,
    content_selections: dict,
    analyzed_charts: list
) -> str:
    """Build a context string from user's content selections."""
    context_parts = []
    
    # Fund info
    fund_info = document_analysis.get("fund_info", {})
    if fund_info:
        context_parts.append(f"**Fund Information:**")
        context_parts.append(f"- Name: {fund_info.get('name', 'Unknown')}")
        context_parts.append(f"- Type: {fund_info.get('type', 'Unknown')}")
        context_parts.append(f"- Period: {fund_info.get('period', 'Unknown')}")
        context_parts.append("")
    
    # Selected sections
    selected_sections = content_selections.get("selected_sections", [])
    all_sections = document_analysis.get("sections", [])
    if selected_sections:
        context_parts.append("**Selected Document Sections:**")
        for section in all_sections:
            if section.get("title") in selected_sections:
                context_parts.append(f"\n## {section['title']}")
                context_parts.append(section.get("summary", ""))
                if section.get("key_points"):
                    for point in section["key_points"]:
                        context_parts.append(f"- {point}")
        context_parts.append("")
    
    # Selected tables
    selected_tables = content_selections.get("selected_tables", [])
    all_tables = document_analysis.get("tables", [])
    if selected_tables:
        context_parts.append("**Selected Tables:**")
        for table in all_tables:
            table_name = f"{table.get('title', 'Table')} (Page {table.get('page', '?')})"
            if table_name in selected_tables:
                context_parts.append(f"\n### {table['title']}")
                context_parts.append(f"Type: {table.get('type', 'Unknown')}")
                if table.get("key_data"):
                    for item in table["key_data"]:
                        context_parts.append(f"- {item}")
        context_parts.append("")
    
    # Selected charts
    selected_chart_ids = content_selections.get("selected_charts", [])
    if selected_chart_ids and analyzed_charts:
        context_parts.append("**Selected Charts Analysis:**")
        for chart in analyzed_charts:
            chart_id = f"chart_{chart.get('page', 0)}_{chart.get('index', 0)}"
            if chart_id in selected_chart_ids:
                context_parts.append(f"\n### Chart on Page {chart.get('page', '?')}")
                context_parts.append(chart.get("description", ""))
                if chart.get("data_points"):
                    context_parts.append("Key data points:")
                    for point in chart.get("data_points", []):
                        context_parts.append(f"- {point}")
        context_parts.append("")
    
    # Selected companies
    selected_companies = content_selections.get("selected_companies", [])
    all_companies = document_analysis.get("companies", [])
    if selected_companies:
        context_parts.append("**Selected Companies:**")
        for company in all_companies:
            if company.get("name") in selected_companies:
                context_parts.append(f"- {company['name']}: {company.get('context', '')}")
        context_parts.append("")
    
    # Selected metrics
    selected_metrics = content_selections.get("selected_metrics", [])
    all_metrics = document_analysis.get("metrics", [])
    if selected_metrics:
        context_parts.append("**Selected Metrics:**")
        for metric in all_metrics:
            metric_name = f"{metric.get('name', 'Metric')}: {metric.get('value', '')}"
            if metric_name in selected_metrics:
                context_parts.append(f"- {metric_name}")
                if metric.get("context"):
                    context_parts.append(f"  Context: {metric['context']}")
        context_parts.append("")
    
    # Selected themes
    selected_themes = content_selections.get("selected_themes", [])
    all_themes = document_analysis.get("themes", [])
    if selected_themes:
        context_parts.append("**Selected Themes:**")
        for theme in all_themes:
            # Support both "name" and "theme" keys from different sources
            theme_name = theme.get("name") or theme.get("theme", "Unknown")
            if theme_name in selected_themes:
                context_parts.append(f"- {theme_name}: {theme.get('description', '')}")
        context_parts.append("")
    
    # Key insights
    key_insights = document_analysis.get("key_insights", [])
    if key_insights:
        context_parts.append("**Key Insights from Document:**")
        for insight in key_insights:
            context_parts.append(f"- {insight}")
        context_parts.append("")
    
    return "\n".join(context_parts)


def _extract_pdf_data(pdf_bytes: bytes) -> ExtractedData:
    """Extract all data from PDF bytes using Docling if available."""
    
    # Try Docling first for better structure-aware extraction
    docling_result = None
    raw_text = ""
    
    try:
        from processing.docling_processor import get_processor
        processor = get_processor()
        if processor.is_available:
            docling_result = processor.process_document(pdf_bytes)
            raw_text = docling_result.get("markdown", "") or docling_result.get("text", "")
    except Exception as e:
        print(f"Docling extraction failed, falling back to basic: {e}")
        docling_result = None
    
    # Fallback to basic text extraction
    if not raw_text:
        text_extractor = TextExtractor()
        text_result = text_extractor.extract_from_bytes(pdf_bytes)
        raw_text = text_result.get("full_text", "")
    
    # Table extraction (always use pdfplumber for reliability)
    table_extractor = TableExtractor()
    tables = table_extractor.extract_from_bytes(pdf_bytes)
    
    # Metadata extraction
    metadata_extractor = MetadataExtractor()
    metadata = metadata_extractor.extract_from_text(raw_text)
    
    # Image extraction (basic for now)
    image_extractor = ImageExtractor()
    images = image_extractor.extract_charts_only(pdf_bytes)
    
    # Analyze charts with Gemini Vision if API key available
    chart_descriptions = []
    if config.GEMINI_API_KEY and images:
        try:
            chart_analyzer = ChartAnalyzer(
                api_key=config.GEMINI_API_KEY,
                model_name=config.GEMINI_FLASH_MODEL
            )
            fund_context = f"Fund: {metadata.get('fund_name', 'Unknown')}, Period: {metadata.get('report_period', 'Unknown')}"
            chart_descriptions = chart_analyzer.analyze_multiple_charts(images, fund_context)
        except Exception as e:
            # Fallback to basic descriptions
            chart_descriptions = [f"Chart on page {img['page']} (vision analysis failed)" for img in images[:5]]
    else:
        chart_descriptions = [f"Chart on page {img['page']}" for img in images[:5]]
    
    # Store ALL raw tables for the agent
    raw_tables = []
    for table in tables:
        raw_tables.append(TableData(
            page=table.get("page", 0),
            table_type=table.get("type", "unknown"),
            headers=table.get("headers", []),
            rows=table.get("rows", [])[:20]  # Limit rows per table
        ))
    
    # Parse holdings from tables
    holdings = []
    for table in tables:
        if table.get("type") == "holdings":
            rows = table_extractor.table_to_dict_list(table)
            for row in rows[:10]:
                name = row.get("Holding", row.get("Company", row.get("Stock", "")))
                weight_str = row.get("Weight", row.get("%", ""))
                weight = None
                if weight_str:
                    try:
                        weight = float(weight_str.replace("%", "").strip())
                    except:
                        pass
                if name:
                    holdings.append(HoldingData(name=name, weight=weight))
    
    # Parse sectors from tables
    sectors = []
    for table in tables:
        if table.get("type") == "sector_allocation":
            rows = table_extractor.table_to_dict_list(table)
            for row in rows[:10]:
                sector_name = row.get("Sector", row.get("Industry", ""))
                weight_str = row.get("Weight", row.get("%", row.get("Allocation", "")))
                if sector_name and weight_str:
                    try:
                        weight = float(weight_str.replace("%", "").strip())
                        sectors.append(SectorData(sector=sector_name, weight=weight))
                    except:
                        pass
    
    # Performance data from metadata
    perf_numbers = metadata_extractor.extract_performance_numbers(raw_text)
    performance = None
    if any(perf_numbers.values()):
        performance = PerformanceData(
            fund_return=perf_numbers.get("fund_return"),
            benchmark_return=perf_numbers.get("benchmark_return"),
            period=metadata.get("report_period")
        )
        if performance.fund_return and performance.benchmark_return:
            performance.outperformance = performance.fund_return - performance.benchmark_return
    
    extracted = ExtractedData(
        fund_name=metadata.get("fund_name"),
        report_period=metadata.get("report_period"),
        benchmark_index=metadata.get("benchmark_index"),
        currency=metadata.get("currency"),
        performance=performance,
        holdings=holdings,
        sectors=sectors,
        raw_text=raw_text,
        raw_tables=raw_tables,
        chart_descriptions=chart_descriptions
    )
    
    # Store Docling result for hybrid chunking (temporary, not serialized)
    if docling_result:
        extracted._docling_result = docling_result
    
    return extracted


if __name__ == "__main__":
    main()
