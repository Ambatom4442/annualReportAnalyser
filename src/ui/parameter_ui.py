"""
Dynamic parameter selection UI component.
"""
from typing import Optional, List
import streamlit as st

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.extracted_data import ExtractedData
from models.comment_params import CommentParameters


def render_parameter_ui(extracted_data: ExtractedData) -> Optional[CommentParameters]:
    """
    Render dynamic parameter UI based on extracted content.
    
    Args:
        extracted_data: The extracted data from the PDF
        
    Returns:
        CommentParameters if user confirms, None otherwise
    """
    st.subheader("📊 Detected Content")
    
    # Show what was detected from the PDF
    _render_content_summary(extracted_data)
    
    st.divider()
    st.subheader("🎛️ Comment Parameters")
    
    # Comment type selection
    comment_type = st.selectbox(
        "Comment Type",
        options=[
            "asset_manager_comment",
            "performance_summary",
            "risk_analysis",
            "sustainability_report",
            "newsletter_excerpt",
            "custom"
        ],
        format_func=lambda x: {
            "asset_manager_comment": "📝 Asset Manager Comment",
            "performance_summary": "📈 Performance Summary",
            "risk_analysis": "⚠️ Risk Analysis",
            "sustainability_report": "🌱 Sustainability Report",
            "newsletter_excerpt": "📰 Newsletter Excerpt",
            "custom": "✏️ Custom"
        }.get(x, x),
        index=0
    )
    
    # Dynamic sections based on comment type
    col1, col2 = st.columns(2)
    
    with col1:
        # Time period
        time_period = None
        if extracted_data.report_period:
            time_period = st.text_input(
                "Time Period",
                value=extracted_data.report_period,
                help="The time period for the comment"
            )
        
        # Benchmark comparison
        compare_benchmark = True
        if extracted_data.benchmark_index:
            compare_benchmark = st.checkbox(
                f"Compare to benchmark ({extracted_data.benchmark_index})",
                value=True
            )
        else:
            compare_benchmark = st.checkbox(
                "Compare to benchmark",
                value=False,
                disabled=True,
                help="No benchmark detected in document"
            )
    
    with col2:
        # Tone
        tone = st.selectbox(
            "Tone",
            options=["formal", "conversational", "technical"],
            format_func=lambda x: {
                "formal": "📋 Formal",
                "conversational": "💬 Conversational", 
                "technical": "🔬 Technical"
            }.get(x, x),
            index=0
        )
        
        # Length
        length = st.selectbox(
            "Length",
            options=["brief", "medium", "detailed"],
            format_func=lambda x: {
                "brief": "📄 Brief (~100 words)",
                "medium": "📃 Medium (~200 words)",
                "detailed": "📜 Detailed (~400 words)"
            }.get(x, x),
            index=1
        )
    
    st.divider()
    
    # Content selection options
    st.subheader("📋 Content Options")
    
    content_col1, content_col2 = st.columns(2)
    
    with content_col1:
        # Holdings options
        has_holdings = len(extracted_data.holdings) > 0
        top_n_holdings = st.slider(
            "Top Holdings to Include",
            min_value=0,
            max_value=min(10, len(extracted_data.holdings)) if has_holdings else 5,
            value=5 if has_holdings else 0,
            disabled=not has_holdings,
            help="Number of top holdings to highlight" if has_holdings else "No holdings data detected"
        )
        
        include_positive = st.checkbox(
            "Include positive contributors",
            value=True,
            disabled=not has_holdings
        )
        
        include_negative = st.checkbox(
            "Include negative contributors",
            value=True,
            disabled=not has_holdings
        )
    
    with content_col2:
        # Sector options
        has_sectors = len(extracted_data.sectors) > 0
        include_sector_impact = st.checkbox(
            "Include sector impact analysis",
            value=has_sectors,
            disabled=not has_sectors,
            help="Analyze sector allocation impact" if has_sectors else "No sector data detected"
        )
        
        # Charts
        has_charts = len(extracted_data.chart_descriptions) > 0
        include_charts = st.checkbox(
            f"Reference charts ({len(extracted_data.chart_descriptions)} found)",
            value=has_charts,
            disabled=not has_charts
        )
    
    st.divider()
    
    # Custom instructions
    with st.expander("✨ Custom Instructions (Optional)", expanded=comment_type == "custom"):
        custom_instructions = st.text_area(
            "Additional instructions for the AI",
            placeholder="E.g., 'Focus on ESG factors', 'Emphasize the tech sector performance', 'Keep it simple for retail investors'",
            height=100
        )
    
    # Generate button
    st.divider()
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    
    with col_btn2:
        if st.button("🚀 Generate Comment", type="primary", width='stretch'):
            params = CommentParameters(
                comment_type=comment_type,
                time_period=time_period,
                compare_benchmark=compare_benchmark,
                top_n_holdings=top_n_holdings,
                include_positive_contributors=include_positive,
                include_negative_contributors=include_negative,
                include_sector_impact=include_sector_impact,
                tone=tone,
                length=length,
                custom_instructions=custom_instructions if custom_instructions else None
            )
            return params
    
    return None


def _render_content_summary(extracted_data: ExtractedData):
    """Render a summary of detected content."""
    
    # Basic info in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if extracted_data.fund_name:
            st.metric("Fund", extracted_data.fund_name[:30] + "..." if len(extracted_data.fund_name or "") > 30 else extracted_data.fund_name)
        else:
            st.metric("Fund", "Not detected")
    
    with col2:
        if extracted_data.report_period:
            st.metric("Period", extracted_data.report_period)
        else:
            st.metric("Period", "Not detected")
    
    with col3:
        if extracted_data.currency:
            st.metric("Currency", extracted_data.currency)
        else:
            st.metric("Currency", "Not detected")
    
    # Content detection tags
    st.write("**Detected Content:**")
    
    tags = []
    
    if extracted_data.performance:
        if extracted_data.performance.fund_return is not None:
            tags.append(f"📈 Performance ({extracted_data.performance.fund_return:+.2f}%)")
    
    if extracted_data.holdings:
        tags.append(f"📊 Holdings ({len(extracted_data.holdings)})")
    
    if extracted_data.sectors:
        tags.append(f"🏢 Sectors ({len(extracted_data.sectors)})")
    
    if extracted_data.chart_descriptions:
        tags.append(f"📉 Charts ({len(extracted_data.chart_descriptions)})")
    
    if extracted_data.benchmark_index:
        tags.append(f"📐 Benchmark: {extracted_data.benchmark_index}")
    
    if tags:
        # Display tags horizontally
        st.write(" | ".join(tags))
    else:
        st.info("ℹ️ Limited structured data detected. Text will be used for comment generation.")
    
    # Expandable sections for details
    if extracted_data.holdings:
        with st.expander(f"🔍 View Top Holdings ({len(extracted_data.holdings)} detected)"):
            for i, holding in enumerate(extracted_data.holdings[:5]):
                weight_str = f"{holding.weight:.2f}%" if holding.weight else "N/A"
                st.write(f"{i+1}. **{holding.name}** - {weight_str}")
            if len(extracted_data.holdings) > 5:
                st.caption(f"... and {len(extracted_data.holdings) - 5} more")
    
    if extracted_data.sectors:
        with st.expander(f"🔍 View Sector Allocation ({len(extracted_data.sectors)} sectors)"):
            for sector in extracted_data.sectors[:5]:
                st.write(f"• **{sector.sector}**: {sector.weight:.1f}%")
            if len(extracted_data.sectors) > 5:
                st.caption(f"... and {len(extracted_data.sectors) - 5} more")
