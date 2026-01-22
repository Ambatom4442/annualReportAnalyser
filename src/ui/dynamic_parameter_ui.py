"""
Dynamic Parameter UI - Renders UI based on AI-discovered document content.
"""
from typing import Optional, Dict, Any, List
import streamlit as st
from PIL import Image

from models.comment_params import CommentParameters


def render_dynamic_parameter_ui(
    document_analysis: Dict[str, Any],
    analyzed_charts: List[Dict[str, Any]] = None,
    saved_selections: Optional[Dict[str, Any]] = None,
    doc_id: Optional[str] = None,
    document_store = None
) -> Optional[tuple]:
    """
    Render a dynamic UI based on AI-discovered document content.
    
    Args:
        document_analysis: JSON structure from DocumentAnalyzerAgent
        analyzed_charts: List of analyzed chart data with images
        saved_selections: Previously saved user selections (loaded from DB)
        doc_id: Document ID for saving selections
        document_store: DocumentStore instance for persistence
        
    Returns:
        Tuple of (CommentParameters, content_selections dict) if submitted, None otherwise
    """
    
    # Initialize session state for selections
    if "content_selections" not in st.session_state:
        st.session_state.content_selections = {}
    
    # Use saved selections if available
    if saved_selections:
        st.info("📂 Loaded your previous selections for this document")
    
    st.subheader("📊 Document Analysis Results")
    
    # Fund Info Summary
    fund_info = document_analysis.get("fund_info", {})
    _render_fund_info(fund_info)
    
    st.divider()
    
    # Key Insights
    insights = document_analysis.get("key_insights", [])
    if insights:
        with st.expander("💡 Key Insights from Document", expanded=True):
            for insight in insights:
                st.markdown(f"• {insight}")
    
    st.divider()
    st.subheader("🎛️ Select Content to Include")
    
    # Create tabs for different content types
    tabs = st.tabs(["📑 Sections", "📊 Tables", "📈 Charts", "🏢 Companies", "📉 Metrics", "🎯 Themes"])
    
    # Extract saved selection lists
    saved_section_titles = saved_selections.get("selected_sections", []) if saved_selections else []
    saved_table_titles = saved_selections.get("selected_tables", []) if saved_selections else []
    saved_chart_ids = saved_selections.get("selected_charts", []) if saved_selections else []
    saved_company_names = saved_selections.get("selected_companies", []) if saved_selections else []
    saved_metric_names = saved_selections.get("selected_metrics", []) if saved_selections else []
    saved_theme_names = saved_selections.get("selected_themes", []) if saved_selections else []
    
    with tabs[0]:
        selected_sections = _render_sections_selector(
            document_analysis.get("sections", []),
            saved_section_titles
        )
    
    with tabs[1]:
        selected_tables = _render_tables_selector(
            document_analysis.get("tables", []),
            saved_table_titles
        )
    
    with tabs[2]:
        selected_charts = _render_charts_selector(
            analyzed_charts or document_analysis.get("charts", []),
            saved_chart_ids
        )
    
    with tabs[3]:
        selected_companies = _render_companies_selector(
            document_analysis.get("companies", []),
            saved_company_names
        )
    
    with tabs[4]:
        selected_metrics = _render_metrics_selector(
            document_analysis.get("metrics", []),
            saved_metric_names
        )
    
    with tabs[5]:
        selected_themes = _render_themes_selector(
            document_analysis.get("themes", []),
            saved_theme_names
        )
    
    st.divider()
    
    # Comment Configuration
    st.subheader("✍️ Comment Configuration")
    
    # Get saved comment params if available
    saved_params = saved_selections.get("comment_params", {}) if saved_selections else {}
    saved_custom = saved_selections.get("custom_instructions", "") if saved_selections else ""
    
    col1, col2 = st.columns(2)
    
    comment_type_options = [
        "asset_manager_comment",
        "performance_summary",
        "risk_analysis",
        "sustainability_report",
        "newsletter_excerpt",
        "custom"
    ]
    
    with col1:
        comment_type = st.selectbox(
            "Comment Type",
            options=comment_type_options,
            index=comment_type_options.index(saved_params.get("comment_type", "asset_manager_comment")) if saved_params.get("comment_type") in comment_type_options else 0,
            format_func=lambda x: {
                "asset_manager_comment": "📝 Asset Manager Comment",
                "performance_summary": "📈 Performance Summary",
                "risk_analysis": "⚠️ Risk Analysis",
                "sustainability_report": "🌱 Sustainability Report",
                "newsletter_excerpt": "📰 Newsletter Excerpt",
                "custom": "✏️ Custom"
            }.get(x, x)
        )
        
        tone_options = ["formal", "conversational", "technical"]
        tone = st.selectbox(
            "Tone",
            options=tone_options,
            index=tone_options.index(saved_params.get("tone", "formal")) if saved_params.get("tone") in tone_options else 0,
            format_func=lambda x: {
                "formal": "📋 Formal",
                "conversational": "💬 Conversational",
                "technical": "🔬 Technical"
            }.get(x, x)
        )
    
    with col2:
        length_options = ["brief", "medium", "detailed"]
        length = st.selectbox(
            "Length",
            options=length_options,
            index=length_options.index(saved_params.get("length", "medium")) if saved_params.get("length") in length_options else 1,
            format_func=lambda x: {
                "brief": "📄 Brief (~100 words)",
                "medium": "📃 Medium (~250 words)",
                "detailed": "📜 Detailed (~400 words)"
            }.get(x, x)
        )
        
        # Time period dropdown from discovered periods
        time_periods = document_analysis.get("time_periods", [])
        period_options = ["Auto-detect"] + [p.get("period", "") for p in time_periods if p.get("period")]
        selected_period = st.selectbox("Time Period", options=period_options)
        time_period = None if selected_period == "Auto-detect" else selected_period
    
    st.divider()
    
    # Research Summary Section (if available from chat)
    research_summary = st.session_state.get("research_summary", "")
    
    if research_summary:
        st.subheader("📊 Research Summary")
        st.info("💡 This summary was generated from your chat research. It will be included in comment generation.")
        
        with st.expander("View Research Summary", expanded=True):
            st.markdown(research_summary)
        
        use_research = st.checkbox(
            "Include research summary in comment generation", 
            value=True,
            help="Uncheck to exclude the research summary from comment generation"
        )
        
        if st.button("🗑️ Clear Research Summary", key="clear_research_summary"):
            st.session_state.research_summary = ""
            st.session_state.selected_messages = set()
            st.rerun()
        
        st.divider()
    else:
        use_research = False
    
    # Custom Instructions (required as per user request)
    st.subheader("✨ Custom Instructions")
    custom_instructions = st.text_area(
        "Provide specific instructions for comment generation",
        value=saved_custom or "",
        placeholder="""Examples:
• Focus on sustainability and ESG factors
• Emphasize positive contributors with specific news events
• Compare performance to benchmark with exact figures
• Discuss sector allocation impact
• Keep language accessible for retail investors""",
        height=150,
        help="These instructions will guide the AI in generating your comment"
    )
    
    # Combine research summary with custom instructions if enabled
    if use_research and research_summary:
        combined_instructions = f"""RESEARCH FINDINGS FROM CHAT:
{research_summary}

USER INSTRUCTIONS:
{custom_instructions if custom_instructions else "No additional instructions."}"""
        final_instructions = combined_instructions
    else:
        final_instructions = custom_instructions
    
    st.divider()
    
    # Generate button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Generate Comment", type="primary", width='stretch'):
            # Build content selections into parameters
            params = CommentParameters(
                comment_type=comment_type,
                tone=tone,
                length=length,
                time_period=time_period,
                custom_instructions=final_instructions if final_instructions else None,
                # Store selections in a way the agent can use
                compare_benchmark=fund_info.get("benchmark") is not None,
                include_positive_contributors=any(
                    c.get("context") == "positive_contributor" 
                    for c in selected_companies
                ),
                include_negative_contributors=any(
                    c.get("context") == "negative_contributor" 
                    for c in selected_companies
                ),
                include_sector_impact=any(
                    t.get("type") == "sectors" 
                    for t in selected_tables
                ),
                top_n_holdings=len([
                    c for c in selected_companies 
                    if c.get("context") == "top_holding"
                ])
            )
            
            # Store full selections in session state for the agent
            content_selections = {
                "selected_sections": [s.get("title") for s in selected_sections] if selected_sections else [],
                "selected_tables": [f"{t.get('title', 'Table')} (Page {t.get('page', '?')})" for t in selected_tables] if selected_tables else [],
                "selected_charts": [f"chart_{c.get('page', 0)}_{c.get('index', 0)}" for c in selected_charts] if selected_charts else [],
                "selected_companies": [c.get("name") for c in selected_companies] if selected_companies else [],
                "selected_metrics": [f"{m.get('name', 'Metric')}: {m.get('value', '')}" for m in selected_metrics] if selected_metrics else [],
                "selected_themes": [t.get("name") for t in selected_themes] if selected_themes else [],
                "fund_info": fund_info
            }
            
            st.session_state.content_selections = content_selections
            
            # Save selections to database for persistence
            if doc_id and document_store:
                try:
                    comment_params_dict = {
                        "comment_type": comment_type,
                        "tone": tone,
                        "length": length,
                        "time_period": time_period
                    }
                    document_store.save_user_selections(
                        doc_id=doc_id,
                        selections=content_selections,
                        comment_params=comment_params_dict,
                        custom_instructions=custom_instructions
                    )
                    st.toast("💾 Selections saved!")
                except Exception as e:
                    st.warning(f"Could not save selections: {e}")
            
            return (params, content_selections)
    
    return None


def _render_fund_info(fund_info: Dict[str, Any]):
    """Render fund information summary."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Fund", fund_info.get("name", "Not detected")[:25] + "..." if fund_info.get("name") and len(fund_info.get("name", "")) > 25 else fund_info.get("name", "Not detected"))
    with col2:
        st.metric("Period", fund_info.get("report_period", "Not detected"))
    with col3:
        st.metric("Benchmark", fund_info.get("benchmark", "Not detected")[:20] + "..." if fund_info.get("benchmark") and len(fund_info.get("benchmark", "")) > 20 else fund_info.get("benchmark", "Not detected"))
    with col4:
        st.metric("Currency", fund_info.get("currency", "Not detected"))


def _render_sections_selector(sections: List[Dict[str, Any]], saved_titles: List[str] = None) -> List[Dict[str, Any]]:
    """Render section multi-select."""
    if not sections:
        st.info("No distinct sections detected in document")
        return []
    
    st.write("**Select sections to include in comment:**")
    
    selected = []
    for section in sections:
        title = section.get('title', 'Untitled')
        # Default: if no saved selections, select all; otherwise use saved
        default_value = title in saved_titles if saved_titles else True
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.checkbox(
                f"**{title}**",
                value=default_value,
                key=f"section_{section.get('id', '')}"
            ):
                selected.append(section)
        with col2:
            st.caption(section.get('type', ''))
        
        if section.get('summary'):
            st.caption(f"   _{section.get('summary')}_")
    
    return selected


def _render_tables_selector(tables: List[Dict[str, Any]], saved_titles: List[str] = None) -> List[Dict[str, Any]]:
    """Render table multi-select with details."""
    if not tables:
        st.info("No tables detected in document")
        return []
    
    st.write("**Select tables to include:**")
    
    selected = []
    for table in tables:
        title = table.get('title', 'Untitled Table')
        table_key = f"{title} (Page {table.get('page', '?')})"
        # Check if this table was previously selected
        default_value = table_key in saved_titles if saved_titles else table.get('include_by_default', True)
        
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                include = st.checkbox(
                    f"**{title}**",
                    value=default_value,
                    key=f"table_{table.get('id', '')}"
                )
            with col2:
                st.caption(f"Type: {table.get('type', 'unknown')}")
            with col3:
                st.caption(f"Rows: {table.get('row_count', '?')}")
            
            if table.get('description'):
                st.caption(f"   {table.get('description')}")
            
            if table.get('key_data'):
                with st.expander("Preview key data"):
                    st.write(", ".join(str(d) for d in table.get('key_data', [])[:10]))
            
            if include:
                selected.append(table)
            
            st.markdown("---")
    
    return selected


def _render_charts_selector(charts: List[Dict[str, Any]], saved_chart_ids: List[str] = None) -> List[Dict[str, Any]]:
    """Render chart selector with image previews."""
    if not charts:
        st.info("No charts detected in document")
        return []
    
    st.write("**Select charts to reference in comment:**")
    
    selected = []
    
    # Display in grid
    cols_per_row = 2
    for i in range(0, len(charts), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            if i + j < len(charts):
                chart = charts[i + j]
                chart_id = f"chart_{chart.get('page', 0)}_{chart.get('index', i+j)}"
                # Check if saved
                default_value = chart_id in saved_chart_ids if saved_chart_ids else chart.get('include_by_default', True)
                
                with col:
                    # Show image if available
                    if chart.get("image") is not None:
                        try:
                            st.image(chart["image"], width='stretch')
                        except:
                            st.caption(f"[Chart image - Page {chart.get('page', '?')}]")
                    
                    include = st.checkbox(
                        f"**{chart.get('title', f'Chart {i+j+1}')}**",
                        value=default_value,
                        key=f"chart_{chart.get('id', i+j)}"
                    )
                    
                    st.caption(f"Type: {chart.get('type', 'unknown')}")
                    
                    if chart.get('description'):
                        with st.expander("Description"):
                            st.write(chart.get('description', '')[:300])
                    
                    if include:
                        selected.append(chart)
    
    return selected


def _render_companies_selector(companies: List[Dict[str, Any]], saved_names: List[str] = None) -> List[Dict[str, Any]]:
    """Render company multi-select grouped by context."""
    if not companies:
        st.info("No specific companies detected in document")
        return []
    
    # Group by context
    contexts = {
        "positive_contributor": ("📈 Positive Contributors", []),
        "negative_contributor": ("📉 Negative Contributors", []),
        "top_holding": ("💼 Top Holdings", []),
        "mentioned": ("📝 Other Mentions", [])
    }
    
    for company in companies:
        ctx = company.get("context", "mentioned")
        if ctx in contexts:
            contexts[ctx][1].append(company)
    
    selected = []
    
    for ctx_key, (label, ctx_companies) in contexts.items():
        if ctx_companies:
            st.write(f"**{label}:**")
            
            # Multi-select for this group
            options = [c.get("name", "Unknown") for c in ctx_companies]
            # Use saved selections or default to all
            defaults = [n for n in options if n in saved_names] if saved_names else options
            
            chosen = st.multiselect(
                f"Select from {label.lower()}",
                options=options,
                default=defaults,
                key=f"companies_{ctx_key}",
                label_visibility="collapsed"
            )
            
            for company in ctx_companies:
                if company.get("name") in chosen:
                    selected.append(company)
                    if company.get("details"):
                        st.caption(f"   _{company.get('name')}: {company.get('details')}_")
    
    return selected


def _render_metrics_selector(metrics: List[Dict[str, Any]], saved_names: List[str] = None) -> List[Dict[str, Any]]:
    """Render metrics selector grouped by category."""
    if not metrics:
        st.info("No specific metrics extracted from document")
        return []
    
    # Group by category
    categories = {}
    for metric in metrics:
        cat = metric.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(metric)
    
    selected = []
    
    for category, cat_metrics in categories.items():
        st.write(f"**{category.title()} Metrics:**")
        
        for metric in cat_metrics:
            name = metric.get("name", "Unknown")
            value = metric.get("value", "")
            metric_key = f"{name}: {value}"
            default_value = metric_key in saved_names if saved_names else True
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.checkbox(
                    name,
                    value=default_value,
                    key=f"metric_{name}_{category}"
                ):
                    selected.append(metric)
            with col2:
                st.write(f"**{value or 'N/A'}**")
    
    return selected


def _render_themes_selector(themes: List[Dict[str, Any]], saved_names: List[str] = None) -> List[Dict[str, Any]]:
    """Render theme/topic selector."""
    if not themes:
        st.info("No specific themes detected in document")
        return []
    
    st.write("**Select themes to emphasize:**")
    
    selected = []
    
    for theme in themes:
        col1, col2 = st.columns([3, 1])
        
        # Support both "theme" and "name" keys from different sources
        theme_name = theme.get("name") or theme.get("theme", "Unknown")
        
        with col1:
            relevance = theme.get("relevance", "medium")
            # Use saved or default based on relevance
            default = theme_name in saved_names if saved_names else relevance in ["high", "medium"]
            
            if st.checkbox(
                f"**{theme_name}**",
                value=default,
                key=f"theme_{theme_name}"
            ):
                selected.append(theme)
        
        with col2:
            relevance_colors = {
                "high": "🔴",
                "medium": "🟡", 
                "low": "🟢"
            }
            st.write(f"{relevance_colors.get(relevance, '⚪')} {relevance}")
        
        if theme.get("description"):
            st.caption(f"   _{theme.get('description')}_")
    
    return selected
