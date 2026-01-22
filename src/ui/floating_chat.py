"""
Floating chat sidebar component for quick document Q&A during comment generation.
"""
import streamlit as st
from typing import Optional, Any


def inject_floating_chat_css(is_open: bool = False):
    """Inject CSS for the floating chat panel on the right side."""
    # Dynamic width based on state
    panel_transform = "translateX(0)" if is_open else "translateX(100%)"
    
    st.markdown(f"""
    <style>
    /* Floating chat panel - overlays on top of content */
    .floating-chat-overlay {{
        position: fixed;
        right: 0;
        top: 0;
        width: 40%;
        min-width: 350px;
        max-width: 500px;
        height: 100vh;
        background: #0e1117;
        border-left: 2px solid #262730;
        box-shadow: -5px 0 25px rgba(0, 0, 0, 0.5);
        z-index: 999999;
        transform: {panel_transform};
        transition: transform 0.3s ease;
        display: flex;
        flex-direction: column;
    }}
    
    .floating-chat-header {{
        padding: 15px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-shrink: 0;
    }}
    
    .floating-chat-header h3 {{
        margin: 0;
        font-size: 18px;
        font-weight: 600;
    }}
    
    .floating-chat-header .doc-name {{
        font-size: 12px;
        opacity: 0.9;
        margin-top: 4px;
    }}
    
    .floating-chat-close {{
        background: rgba(255,255,255,0.2);
        border: none;
        color: white;
        font-size: 20px;
        cursor: pointer;
        padding: 5px 10px;
        border-radius: 5px;
        transition: background 0.2s;
    }}
    
    .floating-chat-close:hover {{
        background: rgba(255,255,255,0.3);
    }}
    
    .floating-chat-body {{
        flex: 1;
        overflow-y: auto;
        padding: 15px;
        background: #0e1117;
    }}
    
    .floating-chat-input {{
        padding: 15px;
        border-top: 1px solid #262730;
        background: #0e1117;
        flex-shrink: 0;
    }}
    
    /* Floating toggle button */
    .chat-toggle-btn {{
        position: fixed;
        right: 20px;
        bottom: 20px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        z-index: 999998;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        transition: all 0.3s ease;
    }}
    
    .chat-toggle-btn:hover {{
        transform: scale(1.1);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }}
    
    /* Hide toggle when panel is open */
    .chat-toggle-btn.hidden {{
        display: none;
    }}
    </style>
    """, unsafe_allow_html=True)


def init_floating_chat_state():
    """Initialize session state for floating chat."""
    if "floating_chat_open" not in st.session_state:
        st.session_state.floating_chat_open = False
    if "floating_chat_messages" not in st.session_state:
        st.session_state.floating_chat_messages = []
    if "floating_chat_agent" not in st.session_state:
        st.session_state.floating_chat_agent = None


def render_floating_chat_toggle():
    """Render the floating chat toggle button."""
    # Use a column trick to place the button
    col1, col2 = st.columns([20, 1])
    
    with col2:
        if st.button("💬", key="floating_chat_toggle_btn", help="Open Chat Assistant"):
            st.session_state.floating_chat_open = not st.session_state.floating_chat_open
            st.rerun()


def render_floating_chat_panel(
    agent: Any,
    current_doc_id: Optional[str] = None,
    document_name: str = "Document",
    secondary_store: Optional[Any] = None,
    secondary_processor: Optional[Any] = None
) -> None:
    """
    Render the floating chat panel in the sidebar area.
    
    Since Streamlit doesn't support true floating panels,
    we use an expander in a right column approach.
    
    Args:
        agent: CommentGeneratorAgent with chat capabilities
        current_doc_id: Current document ID for context
        document_name: Name of the current document
        secondary_store: SecondarySourceStore instance for managing sources
        secondary_processor: SecondarySourceProcessor instance for processing
    """
    init_floating_chat_state()
    
    # Check if chat should be shown
    if not st.session_state.floating_chat_open:
        return
    
    # Render chat panel in the right portion of the screen
    st.markdown("---")
    
    # Chat header
    chat_col1, chat_col2 = st.columns([5, 1])
    with chat_col1:
        st.markdown("### 💬 Quick Chat")
        st.caption(f"Ask about: {document_name}")
    with chat_col2:
        if st.button("✕", key="close_floating_chat", help="Close chat"):
            st.session_state.floating_chat_open = False
            st.rerun()
    
    # Secondary Sources Management - Add before chat
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
    
    # Chat messages container
    chat_container = st.container(height=300)
    
    with chat_container:
        if not st.session_state.floating_chat_messages:
            st.info("💡 Ask questions about the document while generating your comment!")
        else:
            for msg in st.session_state.floating_chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about the document...", key="floating_chat_input"):
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
        if st.button("🗑️ Clear Chat", key="clear_floating_chat"):
            st.session_state.floating_chat_messages = []
            if hasattr(agent, 'clear_memory'):
                agent.clear_memory()
            st.rerun()


def render_chat_sidebar(
    agent: Any,
    current_doc_id: Optional[str] = None,
    document_name: str = "Document"
) -> bool:
    """
    Render chat as a right sidebar using Streamlit's native components.
    Returns True if chat is open (so main content can adjust).
    
    Args:
        agent: CommentGeneratorAgent with chat capabilities
        current_doc_id: Current document ID for context
        document_name: Name of the current document
    
    Returns:
        bool: Whether the chat panel is open
    """
    init_floating_chat_state()
    
    return st.session_state.floating_chat_open


def get_chat_agent(config, vec_store, doc_store):
    """
    Get or create the floating chat agent.
    Reuses the same agent instance for memory persistence.
    """
    if st.session_state.floating_chat_agent is None:
        from agents.comment_agent import CommentGeneratorAgent
        st.session_state.floating_chat_agent = CommentGeneratorAgent(
            api_key=config.GEMINI_API_KEY,
            model_name=config.GEMINI_MODEL,
            provider="gemini",
            vector_store=vec_store,
            document_store=doc_store
        )
    return st.session_state.floating_chat_agent


def render_overlay_chat_sidebar(
    agent: Any,
    current_doc_id: Optional[str] = None,
    document_name: str = "Document"
) -> None:
    """
    Render the floating overlay chat sidebar.
    Uses Streamlit's sidebar for the actual chat, but styled as an overlay.
    """
    init_floating_chat_state()
    
    if not st.session_state.floating_chat_open:
        return
    
    # Use streamlit's native sidebar but make it appear on right via CSS
    with st.sidebar:
        # Add to secondary sidebar section
        st.markdown("---")
        st.markdown("### 💬 Quick Chat")
        st.caption(f"📄 {document_name}")
        
        # Close button
        if st.button("✕ Close Chat", key="close_overlay_chat", use_container_width=True):
            st.session_state.floating_chat_open = False
            st.rerun()
        
        st.divider()
        
        # Chat messages
        chat_container = st.container(height=350)
        with chat_container:
            if not st.session_state.floating_chat_messages:
                st.info("💡 Ask questions about the document!")
            else:
                for msg in st.session_state.floating_chat_messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask...", key="overlay_chat_input"):
            st.session_state.floating_chat_messages.append({
                "role": "user",
                "content": prompt
            })
            
            with st.spinner("..."):
                try:
                    response = agent.chat(prompt, doc_id=current_doc_id)
                    st.session_state.floating_chat_messages.append({
                        "role": "assistant",
                        "content": response
                    })
                except Exception as e:
                    st.session_state.floating_chat_messages.append({
                        "role": "assistant",
                        "content": f"Error: {str(e)}"
                    })
            st.rerun()
        
        # Clear button
        if st.session_state.floating_chat_messages:
            if st.button("🗑️ Clear", key="clear_overlay_chat", use_container_width=True):
                st.session_state.floating_chat_messages = []
                if hasattr(agent, 'clear_memory'):
                    agent.clear_memory()
                st.rerun()

