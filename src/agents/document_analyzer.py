"""
Document Analyzer Agent - Analyzes entire document and returns structured content discovery.
"""
from typing import Optional, List, Dict, Any
import json

import google.generativeai as genai


class DocumentAnalyzerAgent:
    """
    Analyzes a document and returns structured JSON describing all content.
    This enables dynamic UI generation based on actual document contents.
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
    def analyze_document(
        self, 
        raw_text: str, 
        tables_data: List[Dict[str, Any]], 
        chart_images: List[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze entire document and return structured content discovery.
        
        Returns a JSON structure with:
        - sections: List of document sections found
        - tables: List of tables with descriptions
        - charts: List of charts with descriptions
        - companies: List of companies mentioned
        - metrics: Key metrics found
        - time_periods: Time periods mentioned
        - themes: Key themes/topics
        """
        
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(raw_text, tables_data)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Parse JSON from response
            json_content = self._extract_json(result_text)
            
            if json_content:
                return json_content
            else:
                # Return a minimal structure if parsing fails
                return self._get_fallback_structure()
                
        except Exception as e:
            print(f"Document analysis failed: {e}")
            return self._get_fallback_structure()
    
    def _build_analysis_prompt(self, raw_text: str, tables_data: List[Dict[str, Any]]) -> str:
        """Build the prompt for document analysis."""
        
        # Format tables for the prompt
        tables_text = ""
        for i, table in enumerate(tables_data[:15]):
            tables_text += f"\n\nTABLE {i+1} (Page {table.get('page', '?')}):\n"
            headers = table.get('headers', [])
            rows = table.get('rows', [])[:10]
            if headers:
                tables_text += f"Headers: {' | '.join(str(h) for h in headers)}\n"
            for row in rows:
                tables_text += f"{' | '.join(str(cell) for cell in row)}\n"
        
        prompt = f"""Analyze this fund annual report document and extract ALL content into a structured JSON format.

DOCUMENT TEXT:
{raw_text[:15000]}

TABLES FOUND:
{tables_text}

Return a JSON object with this EXACT structure (no markdown, just pure JSON):
{{
    "fund_info": {{
        "name": "fund name if found",
        "benchmark": "benchmark index if found",
        "currency": "currency if found",
        "report_period": "reporting period if found",
        "report_type": "annual/semi-annual/quarterly/monthly"
    }},
    "sections": [
        {{
            "id": "section_1",
            "title": "Section title",
            "type": "performance|holdings|sectors|commentary|sustainability|risk|fees|other",
            "summary": "Brief 1-2 sentence summary of this section",
            "page_hint": "approximate page or 'multiple'"
        }}
    ],
    "tables": [
        {{
            "id": "table_1",
            "title": "Descriptive title for this table",
            "type": "holdings|performance|sectors|regions|risk|fees|returns|other",
            "description": "What data this table contains",
            "key_data": ["list", "of", "key", "values", "from", "table"],
            "row_count": 10,
            "include_by_default": true
        }}
    ],
    "charts": [
        {{
            "id": "chart_1", 
            "title": "Chart title or description",
            "type": "performance|allocation|comparison|trend|other",
            "description": "What this chart shows",
            "include_by_default": true
        }}
    ],
    "companies": [
        {{
            "name": "Company Name",
            "context": "positive_contributor|negative_contributor|top_holding|mentioned",
            "details": "Brief context about this company in the report"
        }}
    ],
    "metrics": [
        {{
            "name": "Metric name (e.g., YTD Return, Sharpe Ratio)",
            "value": "The value",
            "category": "performance|risk|fees|other"
        }}
    ],
    "time_periods": [
        {{
            "period": "December 2023",
            "type": "reporting_period|comparison_period|mentioned"
        }}
    ],
    "themes": [
        {{
            "theme": "Theme name (e.g., ESG, Technology, Sustainability)",
            "relevance": "high|medium|low",
            "description": "How this theme appears in the document"
        }}
    ],
    "key_insights": [
        "List of 3-5 key takeaways from the document"
    ]
}}

IMPORTANT:
1. Extract REAL data from the document - do not make up values
2. Include ALL tables you can identify
3. List ALL companies mentioned with their context
4. Identify the main themes/topics discussed
5. Return ONLY valid JSON, no markdown code blocks
"""
        return prompt
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text."""
        # Try to parse directly
        try:
            return json.loads(text)
        except:
            pass
        
        # Try to find JSON in markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Try to find JSON object pattern
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        return None
    
    def _get_fallback_structure(self) -> Dict[str, Any]:
        """Return minimal fallback structure if analysis fails."""
        return {
            "fund_info": {
                "name": None,
                "benchmark": None,
                "currency": None,
                "report_period": None,
                "report_type": None
            },
            "sections": [],
            "tables": [],
            "charts": [],
            "companies": [],
            "metrics": [],
            "time_periods": [],
            "themes": [],
            "key_insights": ["Document analysis could not extract structured data. Using raw text for generation."]
        }
    
    def analyze_charts_with_vision(
        self, 
        chart_images: List[Dict[str, Any]],
        fund_context: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Analyze chart images using vision and return structured descriptions.
        """
        analyzed_charts = []
        
        for i, img_data in enumerate(chart_images[:8]):
            image = img_data.get("image")
            page = img_data.get("page", i + 1)
            
            if image is None:
                continue
            
            prompt = f"""Analyze this chart from a fund report. {fund_context}

Return JSON with this structure (no markdown):
{{
    "id": "chart_{i+1}",
    "title": "descriptive title",
    "type": "performance|allocation|comparison|trend|other",
    "description": "detailed description of what the chart shows",
    "data_points": ["list of key values/percentages visible"],
    "include_by_default": true
}}

Extract ALL visible data points, percentages, and labels."""

            try:
                # Use vision model for chart analysis
                response = self.model.generate_content([prompt, image])
                chart_json = self._extract_json(response.text)
                
                if chart_json:
                    chart_json["page"] = page
                    chart_json["image"] = image  # Keep reference for UI
                    analyzed_charts.append(chart_json)
                else:
                    analyzed_charts.append({
                        "id": f"chart_{i+1}",
                        "title": f"Chart on page {page}",
                        "type": "other",
                        "description": response.text[:500] if response.text else "Chart detected",
                        "page": page,
                        "image": image,
                        "include_by_default": True
                    })
            except Exception as e:
                analyzed_charts.append({
                    "id": f"chart_{i+1}",
                    "title": f"Chart on page {page}",
                    "type": "other", 
                    "description": f"Vision analysis failed: {str(e)}",
                    "page": page,
                    "image": image,
                    "include_by_default": False
                })
        
        return analyzed_charts
