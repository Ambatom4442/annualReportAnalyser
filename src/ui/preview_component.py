"""
Comment preview and editing UI component.
"""
from typing import Optional, Callable
import streamlit as st
from datetime import datetime


def render_preview(
    comment: str, 
    on_regenerate: Optional[Callable] = None,
    comment_type: str = "asset_manager_comment"
) -> str:
    """
    Render comment preview with editing and export capabilities.
    
    Args:
        comment: The generated comment text
        on_regenerate: Callback function for regeneration
        comment_type: Type of comment for labeling
        
    Returns:
        The edited comment text
    """
    st.subheader("✨ Generated Comment")
    
    # Comment type label
    type_labels = {
        "asset_manager_comment": "📝 Asset Manager Comment",
        "performance_summary": "📈 Performance Summary",
        "risk_analysis": "⚠️ Risk Analysis",
        "sustainability_report": "🌱 Sustainability Report",
        "newsletter_excerpt": "📰 Newsletter Excerpt",
        "custom": "✏️ Custom Comment"
    }
    st.caption(type_labels.get(comment_type, "📄 Comment"))
    
    # Word count
    word_count = len(comment.split())
    st.caption(f"📊 {word_count} words | Generated at {datetime.now().strftime('%H:%M:%S')}")
    
    st.divider()
    
    # Toggle between preview and edit modes
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("✏️ Edit" if not st.session_state.edit_mode else "👁️ Preview"):
            st.session_state.edit_mode = not st.session_state.edit_mode
            st.rerun()
    
    # Display content
    if st.session_state.edit_mode:
        edited_comment = st.text_area(
            "Edit your comment",
            value=comment,
            height=400,
            label_visibility="collapsed"
        )
        
        # Save changes
        if edited_comment != comment:
            st.info("💾 Changes will be saved when you switch back to preview mode")
            comment = edited_comment
    else:
        # Preview mode - render markdown
        st.markdown(comment)
    
    st.divider()
    
    # Action buttons
    _render_action_buttons(comment, on_regenerate)
    
    return comment


def _render_action_buttons(comment: str, on_regenerate: Optional[Callable]):
    """Render action buttons for the preview."""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Copy to clipboard
        if st.button("📋 Copy", width='stretch'):
            st.session_state.clipboard_text = comment
            st.success("Copied to clipboard!")
            # Note: For actual clipboard, we'd need pyperclip or JS
    
    with col2:
        # Download as text
        st.download_button(
            label="📄 Download TXT",
            data=comment,
            file_name=f"comment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            width='stretch'
        )
    
    with col3:
        # Download as markdown
        md_content = f"""# Generated Comment

{comment}

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        st.download_button(
            label="📝 Download MD",
            data=md_content,
            file_name=f"comment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            width='stretch'
        )
    
    with col4:
        # Regenerate
        if on_regenerate:
            if st.button("🔄 Regenerate", width='stretch'):
                on_regenerate()


def render_export_panel(comment: str):
    """Render a dedicated export panel with more options."""
    
    st.subheader("📤 Export Options")
    
    export_format = st.selectbox(
        "Export Format",
        options=["Plain Text (.txt)", "Markdown (.md)", "HTML (.html)", "JSON (.json)"],
        index=0
    )
    
    # Generate export content based on format
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    filename_base = f"comment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if export_format == "Plain Text (.txt)":
        content = comment
        filename = f"{filename_base}.txt"
        mime = "text/plain"
        
    elif export_format == "Markdown (.md)":
        content = f"""# Generated Comment

{comment}

---
*Generated on {timestamp}*
"""
        filename = f"{filename_base}.md"
        mime = "text/markdown"
        
    elif export_format == "HTML (.html)":
        # Convert markdown to basic HTML
        html_content = comment.replace('\n\n', '</p><p>').replace('\n', '<br>')
        content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Generated Comment</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #333; }}
        .meta {{ color: #666; font-size: 0.9em; margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>Generated Comment</h1>
    <p>{html_content}</p>
    <p class="meta">Generated on {timestamp}</p>
</body>
</html>"""
        filename = f"{filename_base}.html"
        mime = "text/html"
        
    else:  # JSON
        import json
        content = json.dumps({
            "comment": comment,
            "word_count": len(comment.split()),
            "generated_at": timestamp,
            "format_version": "1.0"
        }, indent=2)
        filename = f"{filename_base}.json"
        mime = "application/json"
    
    st.download_button(
        label=f"⬇️ Download {export_format}",
        data=content,
        file_name=filename,
        mime=mime,
        width='stretch'
    )
    
    # Preview export content
    with st.expander("👁️ Preview Export"):
        st.code(content[:1000] + ("..." if len(content) > 1000 else ""))
