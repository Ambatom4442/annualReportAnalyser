"""
URL content fetching tool for agent - uses Playwright for JS-rendered pages.
No storage - just fetches and returns content for immediate use.
"""
import warnings
import logging
from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Suppress warnings
warnings.filterwarnings("ignore", message="Token indices sequence length")
logging.getLogger("transformers").setLevel(logging.ERROR)


class FetchURLInput(BaseModel):
    """Input for URL fetch tool."""
    url: str = Field(description="The URL to fetch and extract content from")


class FetchURLContentTool(BaseTool):
    """
    Tool for fetching and extracting content from a URL using Playwright.
    
    This tool:
    - Uses headless browser to render JavaScript
    - Extracts full dynamic content
    - Returns clean markdown
    - Does NOT store anything (one-time use)
    """
    
    name: str = "fetch_url_content"
    description: str = """Fetch and extract content from a URL.
    Use this when a user provides a URL in their message and wants information from that page.
    Returns the page content as clean markdown text.
    This is for one-time lookups - content is NOT stored for future searches.
    
    Example: If user asks "What does https://example.com/report say about revenue?"
    Call this tool with the URL to get the page content, then answer their question."""
    args_schema: Type[BaseModel] = FetchURLInput
    
    def __init__(self):
        super().__init__()
    
    def _run(self, url: str) -> str:
        """Fetch URL content using Playwright in a subprocess (avoids event loop issues)."""
        import subprocess
        import sys
        import json
        import tempfile
        import os
        
        try:
            import html2text
        except ImportError:
            return "Error: html2text is required for URL extraction."
        
        # Create a temporary script to run Playwright in isolation
        script = '''
import sys
import json
from playwright.sync_api import sync_playwright

url = sys.argv[1]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        html = page.content()
        print(json.dumps({"html": html}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
    finally:
        browser.close()
'''
        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            # Run in subprocess to completely isolate from Streamlit's event loop
            result = subprocess.run(
                [sys.executable, script_path, url],
                capture_output=True,
                text=True,
                timeout=90
            )
            
            if result.returncode != 0:
                return f"Error fetching URL {url}: {result.stderr}"
            
            # Parse the JSON output
            output = json.loads(result.stdout.strip())
            
            if "error" in output:
                return f"Error fetching URL {url}: {output['error']}"
            
            html_content = output["html"]
            
        except subprocess.TimeoutExpired:
            return f"Error: Timeout while fetching URL {url}"
        except Exception as e:
            return f"Error fetching URL {url}: {str(e)}"
        finally:
            try:
                os.unlink(script_path)
            except:
                pass
        
        # Convert HTML to markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        markdown = h.handle(html_content)
        
        if markdown and len(markdown.strip()) > 100:
            # Truncate if too long
            if len(markdown) > 15000:
                markdown = markdown[:15000] + "\n\n... [Content truncated - page is very long]"
            return f"## Content from {url}\n\n{markdown}"
        
        return f"Could not extract meaningful content from URL: {url}"
    
    async def _arun(self, url: str) -> str:
        """Async execution."""
        return self._run(url)


def create_url_fetch_tool() -> FetchURLContentTool:
    """Create URL fetch tool."""
    return FetchURLContentTool()
