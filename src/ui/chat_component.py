"""
Chat interface component for document Q&A.
"""
import streamlit as st
from typing import Optional, List, Dict, Any


def render_chat_interface(
    agent: Any,
    current_doc_id: Optional[str] = None,
    show_history: bool = True,
    secondary_processor: Optional[Any] = None,
    secondary_store: Optional[Any] = None
) -> None:
    """
    Render a chat interface for document Q&A with attachment support.
    
    Args:
        agent: CommentGeneratorAgent with chat capabilities
        current_doc_id: Optional document ID for context
        show_history: Whether to show chat history
        secondary_processor: SecondarySourceProcessor for handling attachments
        secondary_store: SecondarySourceStore for managing sources
    """
    st.subheader("💬 Chat with Documents")
    
    # Initialize chat history in session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Show attached sources bar if any
    if secondary_processor:
        try:
            from ui.attachment_component import (
                render_attached_sources_bar,
                init_attachment_state
            )
            init_attachment_state()
            render_attached_sources_bar(processor=secondary_processor)
        except ImportError:
            pass
    
    # Display chat history
    if show_history and st.session_state.chat_messages:
        chat_container = st.container(height=400)
        with chat_container:
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
    
    # Input area with attachment button
    col_attach, col_input = st.columns([1, 15])
    
    with col_attach:
        # Attachment button
        if secondary_processor and current_doc_id:
            try:
                from ui.attachment_component import render_attachment_button
                show_menu = render_attachment_button()
            except ImportError:
                show_menu = False
        else:
            show_menu = False
    
    # Show attachment menu if toggled
    if show_menu and secondary_processor and current_doc_id:
        try:
            from ui.attachment_component import render_attachment_menu
            render_attachment_menu(
                parent_doc_id=current_doc_id,
                processor=secondary_processor
            )
        except ImportError:
            pass
    
    # Chat input
    if prompt := st.chat_input("Ask about the documents..."):
        # Add user message
        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = agent.chat(prompt, doc_id=current_doc_id)
                    st.markdown(response)
                    
                    # Add assistant message
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": response
                    })
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    # Bottom controls - Clear Chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_messages = []
        if hasattr(agent, 'clear_memory'):
            agent.clear_memory()
        # Also reset the agent in session state to get fresh memory
        if "chat_agent" in st.session_state:
            del st.session_state.chat_agent
        st.rerun()
    
    # Manage Secondary Sources - full width expander
    if secondary_store and current_doc_id:
        try:
            from ui.attachment_component import render_manage_sources_modal
            render_manage_sources_modal(
                parent_doc_id=current_doc_id,
                secondary_store=secondary_store,
                processor=secondary_processor
            )
        except ImportError:
            pass


def render_document_library(
    documents: List[Dict[str, Any]],
    on_select: Optional[callable] = None,
    on_delete: Optional[callable] = None
) -> Optional[str]:
    """
    Render a document library panel.
    
    Args:
        documents: List of document metadata dicts
        on_select: Callback when document is selected
        on_delete: Callback when document is deleted
    
    Returns:
        Selected document ID or None
    """
    st.subheader("📚 Document Library")
    
    if not documents:
        st.info("No documents uploaded yet. Upload a PDF to get started.")
        return None
    
    selected_id = None
    
    for doc in documents:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{doc.get('filename', 'Unknown')}**")
                st.caption(f"Uploaded: {doc.get('created_at', 'Unknown')[:10] if doc.get('created_at') else 'Unknown'}")
                if doc.get('fund_name'):
                    st.caption(f"Fund: {doc['fund_name']}")
            
            with col2:
                if st.button("📖 Open", key=f"open_{doc['id']}"):
                    selected_id = doc['id']
                    if on_select:
                        on_select(doc['id'])
            
            with col3:
                if on_delete:
                    if st.button("🗑️", key=f"delete_{doc['id']}"):
                        on_delete(doc['id'])
                        st.rerun()
    
    return selected_id


def render_document_comparison(
    documents: List[Dict[str, Any]],
    agent: Any
) -> None:
    """
    Render a document comparison interface.
    
    Args:
        documents: List of document metadata
        agent: CommentGeneratorAgent for analysis
    """
    st.subheader("📊 Compare Documents")
    
    if len(documents) < 2:
        st.info("Upload at least 2 documents to use comparison feature.")
        return
    
    # Document selection
    col1, col2 = st.columns(2)
    
    doc_options = {doc['filename']: doc['id'] for doc in documents}
    
    with col1:
        doc1_name = st.selectbox("Document 1", options=list(doc_options.keys()), key="compare_doc1")
    
    with col2:
        doc2_options = [name for name in doc_options.keys() if name != doc1_name]
        doc2_name = st.selectbox("Document 2", options=doc2_options, key="compare_doc2")
    
    # Comparison type
    comparison_type = st.selectbox(
        "Comparison Type",
        options=["Performance", "Holdings", "Sectors", "Risk Metrics", "Custom"]
    )
    
    if comparison_type == "Custom":
        custom_prompt = st.text_area("What would you like to compare?")
    else:
        custom_prompt = None
    
    if st.button("🔍 Compare"):
        with st.spinner("Analyzing documents..."):
            try:
                # Build comparison query
                if custom_prompt:
                    query = f"Compare these two documents: {custom_prompt}"
                else:
                    query = f"Compare the {comparison_type.lower()} between {doc1_name} and {doc2_name}"
                
                response = agent.chat(query)
                st.markdown(response)
            except Exception as e:
                st.error(f"Comparison failed: {str(e)}")


def render_quick_insights(
    document_analysis: Dict[str, Any],
    agent: Optional[Any] = None
) -> None:
    """
    Render quick insights panel for a document.
    
    Args:
        document_analysis: AI analysis results
        agent: Optional agent for additional queries
    """
    st.subheader("⚡ Quick Insights")
    
    # Fund info
    fund_info = document_analysis.get("fund_info", {})
    if fund_info:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fund Name", fund_info.get("name", "N/A"))
        with col2:
            st.metric("Fund Type", fund_info.get("type", "N/A"))
        with col3:
            st.metric("Period", fund_info.get("period", "N/A"))
    
    # Key metrics
    metrics = document_analysis.get("metrics", [])
    if metrics:
        st.markdown("**Key Metrics:**")
        cols = st.columns(min(len(metrics), 4))
        for i, metric in enumerate(metrics[:4]):
            with cols[i]:
                st.metric(
                    metric.get("name", "Metric"),
                    metric.get("value", "N/A")
                )
    
    # Key insights
    insights = document_analysis.get("key_insights", [])
    if insights:
        st.markdown("**Key Insights:**")
        for insight in insights[:5]:
            st.markdown(f"• {insight}")
    
    # Quick action buttons
    if agent:
        st.markdown("**Quick Actions:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📈 Performance Summary"):
                with st.spinner("Generating..."):
                    response = agent.chat("Summarize the fund performance from this document")
                    st.markdown(response)
        
        with col2:
            if st.button("🏢 Top Holdings"):
                with st.spinner("Generating..."):
                    response = agent.chat("What are the top holdings in this fund?")
                    st.markdown(response)
        
        with col3:
            if st.button("⚠️ Risk Factors"):
                with st.spinner("Generating..."):
                    response = agent.chat("What are the main risk factors mentioned?")
                    st.markdown(response)
