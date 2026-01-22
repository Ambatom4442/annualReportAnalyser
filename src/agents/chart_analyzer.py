"""
Chart analyzer using Gemini Vision to interpret charts and graphs.
"""
from typing import List, Dict, Any, Optional
import base64
import io

import google.generativeai as genai
from PIL import Image


class ChartAnalyzer:
    """Analyze charts using Gemini Vision."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
    def analyze_chart(self, image: Image.Image, context: str = "") -> str:
        """
        Analyze a single chart image and extract insights.
        
        Args:
            image: PIL Image of the chart
            context: Optional context about the fund/report
            
        Returns:
            Text description of the chart's data and insights
        """
        prompt = f"""Analyze this chart from a fund annual report. Extract ALL data points, values, and insights.

Context: {context if context else "This is from a fund annual report."}

Please provide:
1. Chart type (bar, line, pie, etc.)
2. ALL specific values/percentages shown
3. Time periods covered
4. Key trends or patterns
5. Any labels, legends, or annotations
6. Specific company names and their values if shown

Be precise with numbers - extract exact values from the chart.
Format as structured text that can be used for writing a fund commentary."""

        try:
            response = self.model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            return f"Chart analysis failed: {str(e)}"
    
    def analyze_multiple_charts(
        self, 
        images: List[Dict[str, Any]], 
        context: str = ""
    ) -> List[str]:
        """
        Analyze multiple chart images.
        
        Args:
            images: List of image dicts with 'image' (PIL Image) and metadata
            context: Context about the fund
            
        Returns:
            List of chart descriptions
        """
        descriptions = []
        
        for img_data in images:  # Limit to 5 charts
            image = img_data.get("image")
            page = img_data.get("page", "unknown")
            
            if image:
                chart_context = f"{context} This chart is from page {page}."
                description = self.analyze_chart(image, chart_context)
                descriptions.append(f"[Page {page}] {description}")
        
        return descriptions
    
    def analyze_page_for_charts(
        self, 
        page_image: Image.Image, 
        page_num: int,
        context: str = ""
    ) -> str:
        """
        Analyze an entire page image to extract chart/table data.
        Useful when table extraction fails or for complex layouts.
        """
        prompt = f"""Analyze this page from a fund annual report (Page {page_num}).

Context: {context if context else "This is from a fund annual report."}

Extract ALL numerical data visible on this page:
1. Any tables - list all rows with their values
2. Any charts/graphs - extract all data points
3. Performance figures (returns, percentages)
4. Holdings and their weights
5. Sector allocations
6. Any dates, periods, benchmarks mentioned

Be extremely precise with numbers. Format the data clearly."""

        try:
            response = self.model.generate_content([prompt, page_image])
            return response.text
        except Exception as e:
            return f"Page analysis failed: {str(e)}"
