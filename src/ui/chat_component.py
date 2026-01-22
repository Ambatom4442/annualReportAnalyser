"""
Chat interface component for document Q&A.
"""
import streamlit as st
from typing import Optional, List, Dict, Any


def init_research_selection_state():
    """Initialize session state for research message selection."""
    if "selected_messages" not in st.session_state:
        st.session_state.selected_messages = set()
    if "research_summary" not in st.session_state:
        st.session_state.research_summary = ""
    if "selection_mode" not in st.session_state:
        st.session_state.selection_mode = False


def generate_research_summary(messages: List[Dict[str, str]], agent: Any) -> str:
    """
    Generate a summary from selected chat messages using AI.
    
    Args:
        messages: List of selected messages with role and content
        agent: CommentGeneratorAgent for summarization
    
    Returns:
        Summarized research findings
    """
    if not messages:
        return ""
    
    # Build the conversation to summarize
    conversation_text = ""
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        conversation_text += f"{role}: {msg['content']}\n\n"
    
    # Create summarization prompt
    summary_prompt = f"""Summarize the key findings and data points from this research conversation into concise bullet points that can be used for generating a financial comment.

Focus on:
- Specific numbers, percentages, and metrics
- Key insights about companies, funds, or markets
- Important dates and time periods
- Any comparisons or trends identified

Research Conversation:
{conversation_text}

Provide a structured summary with the most important facts:"""
    
    try:
        # Use the agent to generate summary
        summary = agent.chat(summary_prompt, doc_id=None)
        return summary
    except Exception as e:
        return f"Error generating summary: {str(e)}"


def render_chat_interface(
    agent: Any,
    current_doc_id: Optional[str] = None,
    show_history: bool = True,
    secondary_processor: Optional[Any] = None,
    secondary_store: Optional[Any] = None,
    chat_store: Optional[Any] = None
) -> None:
    """
    Render a chat interface for document Q&A with attachment support.
    
    Args:
        agent: CommentGeneratorAgent with chat capabilities
        current_doc_id: Optional document ID for context
        show_history: Whether to show chat history
        secondary_processor: SecondarySourceProcessor for handling attachments
        secondary_store: SecondarySourceStore for managing sources
        chat_store: ChatStore for persisting chat history
    """
    st.subheader("💬 Chat with Documents")
    
    # Initialize states
    init_research_selection_state()
    
    # Initialize chat history - load from database if available
    chat_key = f"chat_messages_{current_doc_id}" if current_doc_id else "chat_messages"
    
    if chat_key not in st.session_state:
        # Try to load from database
        if chat_store and current_doc_id:
            saved_messages = chat_store.get_messages(current_doc_id, chat_type="main")
            st.session_state[chat_key] = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in saved_messages
            ]
        else:
            st.session_state[chat_key] = []
    
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
    
    # Selection mode toggle and actions
    if st.session_state[chat_key]:
        sel_col1, sel_col2, sel_col3 = st.columns([2, 2, 2])
        
        with sel_col1:
            selection_mode = st.toggle(
                "📋 Select Messages", 
                value=st.session_state.selection_mode,
                help="Enable to select messages for research summary"
            )
            if selection_mode != st.session_state.selection_mode:
                st.session_state.selection_mode = selection_mode
                st.rerun()
        
        with sel_col2:
            if st.session_state.selection_mode:
                selected_count = len(st.session_state.selected_messages)
                st.caption(f"✅ {selected_count} message(s) selected")
        
        with sel_col3:
            if st.session_state.selection_mode and st.session_state.selected_messages:
                if st.button("📝 Create Summary", type="primary", use_container_width=True):
                    # Get selected messages
                    messages = st.session_state[chat_key]
                    selected_msgs = [
                        messages[i] for i in sorted(st.session_state.selected_messages)
                        if i < len(messages)
                    ]
                    
                    with st.spinner("🤖 Generating research summary..."):
                        summary = generate_research_summary(selected_msgs, agent)
                        st.session_state.research_summary = summary
                    st.success("✅ Summary created! View it in Generate Comment step")
                    st.rerun()
    
    # Display chat history with optional selection
    if show_history and st.session_state[chat_key]:
        chat_container = st.container(height=400)
        with chat_container:
            for idx, msg in enumerate(st.session_state[chat_key]):
                if st.session_state.selection_mode:
                    # Selection mode: show checkboxes
                    msg_col1, msg_col2 = st.columns([1, 15])
                    
                    with msg_col1:
                        is_selected = idx in st.session_state.selected_messages
                        if st.checkbox(
                            "Select message", 
                            value=is_selected, 
                            key=f"sel_msg_{idx}",
                            label_visibility="collapsed"
                        ):
                            st.session_state.selected_messages.add(idx)
                        else:
                            st.session_state.selected_messages.discard(idx)
                    
                    with msg_col2:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])
                else:
                    # Normal mode: just show messages
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
        st.session_state[chat_key].append({
            "role": "user",
            "content": prompt
        })
        
        # Save to database
        if chat_store and current_doc_id:
            chat_store.save_message(current_doc_id, "user", prompt, chat_type="main")
        
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
                    st.session_state[chat_key].append({
                        "role": "assistant",
                        "content": response
                    })
                    
                    # Save to database
                    if chat_store and current_doc_id:
                        chat_store.save_message(current_doc_id, "assistant", response, chat_type="main")
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state[chat_key].append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    # Bottom controls - Clear Chat button
    col_clear1, col_clear2 = st.columns([1, 1])
    
    with col_clear1:
        if st.button("🗑️ Clear Chat"):
            st.session_state[chat_key] = []
            st.session_state.selected_messages = set()
            st.session_state.selection_mode = False
            if hasattr(agent, 'clear_memory'):
                agent.clear_memory()
            # Clear from database
            if chat_store and current_doc_id:
                chat_store.clear_history(current_doc_id, chat_type="main")
            # Also reset the agent in session state to get fresh memory
            if "chat_agent" in st.session_state:
                del st.session_state.chat_agent
            st.rerun()
    
    with col_clear2:
        if st.session_state.research_summary:
            if st.button("🗑️ Clear Research Summary"):
                st.session_state.research_summary = ""
                st.session_state.selected_messages = set()
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
