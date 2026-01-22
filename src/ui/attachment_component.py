"""
UI component for managing secondary sources (attachments).
Provides ChatGPT-like file attachment and URL input.
"""
import streamlit as st
from typing import Optional, List, Callable
import uuid


def get_session_id() -> str:
    """Get or create a session ID for tracking temporary sources."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id


def init_attachment_state():
    """Initialize session state for attachments."""
    if "attached_sources" not in st.session_state:
        st.session_state.attached_sources = []  # List of SecondarySource objects
    if "pending_files" not in st.session_state:
        st.session_state.pending_files = []
    if "show_attachment_menu" not in st.session_state:
        st.session_state.show_attachment_menu = False


def render_attachment_button() -> bool:
    """
    Render the attachment button (📎) that toggles the attachment menu.
    
    Returns:
        True if menu should be shown
    """
    init_attachment_state()
    
    if st.button("📎", key="attachment_btn", help="Add supporting sources"):
        st.session_state.show_attachment_menu = not st.session_state.show_attachment_menu
        st.rerun()
    
    return st.session_state.show_attachment_menu


def render_attachment_menu(
    parent_doc_id: str,
    processor,  # SecondarySourceProcessor
    on_source_added: Optional[Callable] = None
):
    """
    Render the attachment menu with file upload, URL input, and stock ticker.
    
    Args:
        parent_doc_id: ID of the primary document to link sources to
        processor: SecondarySourceProcessor instance
        on_source_added: Callback when a source is successfully added
    """
    init_attachment_state()
    session_id = get_session_id()
    
    with st.container():
        st.markdown("##### 📎 Add Supporting Source")
        
        tabs = st.tabs(["📄 Upload File", "🔗 Add URL", "📈 Stock Ticker"])
        
        # Tab 1: File Upload
        with tabs[0]:
            uploaded_file = st.file_uploader(
                "Drop files here or click to browse",
                type=["pdf", "docx", "doc", "txt", "csv", "md"],
                key="secondary_file_uploader",
                help="Supported: PDF, DOCX, TXT, CSV, Markdown"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                is_permanent = st.checkbox("Save permanently", value=False, key="file_permanent")
            
            if uploaded_file:
                with col2:
                    if st.button("➕ Add File", key="add_file_btn", type="primary"):
                        with st.spinner(f"Processing {uploaded_file.name}..."):
                            source, error = processor.process_file(
                                file_content=uploaded_file.read(),
                                filename=uploaded_file.name,
                                parent_doc_id=parent_doc_id,
                                session_id=session_id,
                                is_temporary=not is_permanent
                            )
                            
                            if error:
                                st.error(f"Error: {error}")
                            else:
                                st.session_state.attached_sources.append(source)
                                st.success(f"Added: {uploaded_file.name}")
                                if on_source_added:
                                    on_source_added(source)
                                st.rerun()
        
        # Tab 2: URL Input
        with tabs[1]:
            url = st.text_input(
                "Enter URL",
                placeholder="https://example.com/article",
                key="secondary_url_input"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                url_permanent = st.checkbox("Save permanently", value=False, key="url_permanent")
            
            if url:
                with col2:
                    if st.button("➕ Add URL", key="add_url_btn", type="primary"):
                        with st.spinner("Fetching content..."):
                            source, error = processor.process_url(
                                url=url,
                                parent_doc_id=parent_doc_id,
                                session_id=session_id,
                                is_temporary=not url_permanent
                            )
                            
                            if error:
                                st.error(f"Error: {error}")
                            else:
                                st.session_state.attached_sources.append(source)
                                st.success(f"Added: {source.name}")
                                if on_source_added:
                                    on_source_added(source)
                                st.rerun()
        
        # Tab 3: Stock Ticker
        with tabs[2]:
            st.markdown("Enter a stock ticker to get real-time market data.")
            
            ticker = st.text_input(
                "Stock Ticker",
                placeholder="e.g., AAPL, 7203.T (Toyota)",
                key="stock_ticker_input"
            )
            
            st.caption("**Common tickers:** Toyota (7203.T), Sony (6758.T), Apple (AAPL)")
            
            if ticker:
                if st.button("📈 Fetch Stock Data", key="fetch_stock_btn", type="primary"):
                    try:
                        from agents.tools.stock_tools import get_stock_info, format_stock_data
                        
                        with st.spinner(f"Fetching {ticker}..."):
                            data = get_stock_info(ticker)
                            
                            if "error" in data:
                                st.error(data["error"])
                            else:
                                # Display the data
                                st.markdown(format_stock_data(data))
                                
                                # Store as a "virtual" source (not in vector store, just for context)
                                from models.secondary_source import SecondarySource, SourceType
                                from datetime import datetime
                                
                                source = SecondarySource(
                                    source_id=f"stock_{ticker}_{uuid.uuid4().hex[:8]}",
                                    parent_doc_id=parent_doc_id,
                                    source_type=SourceType.STOCK,
                                    name=f"{data.get('name', ticker)} ({ticker})",
                                    ticker=ticker,
                                    content_md=format_stock_data(data),
                                    is_temporary=True,
                                    session_id=session_id,
                                    is_processed=True,
                                    created_at=datetime.now()
                                )
                                
                                st.session_state.attached_sources.append(source)
                                st.success(f"Added stock data for {ticker}")
                                st.rerun()
                    except ImportError:
                        st.error("yfinance not installed. Run: pip install yfinance")
        
        # Close button
        if st.button("✕ Close", key="close_attachment_menu"):
            st.session_state.show_attachment_menu = False
            st.rerun()


def render_attached_sources_bar(
    processor=None,
    on_source_removed: Optional[Callable] = None
):
    """
    Render the bar showing currently attached sources with remove buttons.
    
    Args:
        processor: SecondarySourceProcessor for deletion
        on_source_removed: Callback when a source is removed
    """
    init_attachment_state()
    
    sources = st.session_state.attached_sources
    if not sources:
        return
    
    # Horizontal display of attached sources
    st.markdown(f"**📎 {len(sources)} Attached:**")
    
    # Create columns for each source (max 4 per row)
    num_cols = min(len(sources), 4)
    cols = st.columns(num_cols)
    
    for i, source in enumerate(sources):
        col_idx = i % num_cols
        
        icon = {
            "pdf": "📄",
            "docx": "📝",
            "txt": "📃",
            "csv": "📊",
            "url": "🔗",
            "stock": "📈"
        }.get(source.source_type.value if hasattr(source.source_type, 'value') else source.source_type, "📎")
        
        # Truncate long names
        label = source.name[:18] + "..." if len(source.name) > 18 else source.name
        
        with cols[col_idx]:
            st.caption(f"{icon} {label}")
            if st.button("✕", key=f"remove_source_{source.source_id}", help=f"Remove"):
                if processor:
                    processor.delete_source(source.source_id)
                st.session_state.attached_sources = [
                    s for s in st.session_state.attached_sources 
                    if s.source_id != source.source_id
                ]
                if on_source_removed:
                    on_source_removed(source)
                st.rerun()


def render_source_selector(
    sources: List,
    key_prefix: str = "source_select"
) -> List:
    """
    Render checkboxes to select which sources to include.
    
    Args:
        sources: List of SecondarySource objects
        key_prefix: Prefix for checkbox keys
    
    Returns:
        List of selected source IDs
    """
    if not sources:
        return []
    
    st.markdown("**📎 Include Secondary Sources:**")
    
    selected = []
    for source in sources:
        icon = {
            "pdf": "📄",
            "docx": "📝", 
            "txt": "📃",
            "csv": "📊",
            "url": "🔗",
            "stock": "📈"
        }.get(source.source_type.value if hasattr(source.source_type, 'value') else source.source_type, "📎")
        
        if st.checkbox(
            f"{icon} {source.name}",
            value=True,
            key=f"{key_prefix}_{source.source_id}"
        ):
            selected.append(source.source_id)
    
    return selected


def render_manage_sources_modal(
    parent_doc_id: str,
    secondary_store,
    processor,
    on_change: Optional[Callable] = None
):
    """
    Render a modal/expander for managing all secondary sources for a document.
    
    Args:
        parent_doc_id: Primary document ID
        secondary_store: SecondarySourceStore instance
        processor: SecondarySourceProcessor instance
        on_change: Callback when sources change
    """
    with st.expander("⚙️ Manage Secondary Sources", expanded=False):
        # Get all sources for this document
        all_sources = secondary_store.get_by_parent(parent_doc_id)
        
        if not all_sources:
            st.info("No secondary sources attached to this document.")
        else:
            st.markdown(f"**📎 {len(all_sources)} Source(s) Attached**")
            
            for source in all_sources:
                icon = {
                    "pdf": "📄",
                    "docx": "📝",
                    "txt": "📃",
                    "csv": "📊",
                    "url": "🔗",
                    "stock": "📈"
                }.get(source.source_type.value if hasattr(source.source_type, 'value') else source.source_type, "📎")
                
                # Horizontal layout with better proportions
                # Name (50%) | Type (10%) | Status (15%) | Save (10%) | Delete (10%)
                col1, col2, col3, col4, col5 = st.columns([5, 1, 1.5, 1, 1])
                
                with col1:
                    st.markdown(f"{icon} **{source.name}**")
                
                with col2:
                    source_type_str = source.source_type.value if hasattr(source.source_type, 'value') else source.source_type
                    st.caption(source_type_str.upper())
                
                with col3:
                    if source.is_temporary:
                        st.caption("🟡 Session")
                    else:
                        st.caption("🟢 Saved")
                
                with col4:
                    if source.is_temporary:
                        if st.button("💾", key=f"save_{source.source_id}", help="Save permanently"):
                            secondary_store.make_permanent(source.source_id)
                            if on_change:
                                on_change()
                            st.rerun()
                
                with col5:
                    if st.button("🗑️", key=f"delete_{source.source_id}", help="Delete"):
                        processor.delete_source(source.source_id)
                        if on_change:
                            on_change()
                        st.rerun()


def get_attached_sources_content() -> str:
    """
    Get the markdown content of all attached sources for context.
    
    Returns:
        Combined markdown content of all attached sources
    """
    init_attachment_state()
    
    sources = st.session_state.attached_sources
    if not sources:
        return ""
    
    content_parts = []
    for source in sources:
        if source.content_md:
            source_type = source.source_type.value if hasattr(source.source_type, 'value') else source.source_type
            content_parts.append(
                f"--- SECONDARY SOURCE: {source.name} (Type: {source_type}) ---\n"
                f"{source.content_md}\n"
                f"--- END {source.name} ---"
            )
    
    return "\n\n".join(content_parts)
