"""
LangChain AgentExecutor for comment generation with tools and memory.
"""
from typing import Optional, List, Dict, Any
import json

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.extracted_data import ExtractedData
from models.comment_params import CommentParameters


class CommentGeneratorAgent:
    """Agent for generating comments using LangChain AgentExecutor with tools and memory."""
    
    def __init__(
        self, 
        api_key: str, 
        model_name: str = "gemini-2.5-pro", 
        provider: str = "gemini",
        vector_store: Optional[Any] = None,
        document_store: Optional[Any] = None
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.provider = provider
        self.vector_store = vector_store
        self.document_store = document_store
        self._llm = None
        self._memory = None
        self._tools = None
        self._agent_executor = None
    
    @property
    def llm(self) -> BaseChatModel:
        """Lazy initialization of LLM."""
        if self._llm is None:
            if self.provider == "openai":
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.model_name,
                    api_key=self.api_key,
                    temperature=0.7,
                    max_tokens=4096
                )
            else:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.7,
                    max_output_tokens=4096
                )
        return self._llm
    
    @property
    def memory(self) -> ConversationBufferMemory:
        """Get or create conversation memory."""
        if self._memory is None:
            self._memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="output"  # Explicitly set to avoid warning with intermediate_steps
            )
        return self._memory
    
    @property
    def tools(self) -> List:
        """Get or create agent tools."""
        if self._tools is None:
            self._tools = []
            
            if self.vector_store and self.document_store:
                try:
                    from agents.tools.search_tools import create_search_tool, create_document_retriever_tool
                    from agents.tools.table_tools import create_table_query_tool, create_compare_tool
                    from agents.tools.calculation_tools import create_calculation_tool, create_extract_numbers_tool
                    
                    self._tools = [
                        create_search_tool(self.vector_store),
                        create_document_retriever_tool(self.vector_store, self.document_store),
                        create_table_query_tool(self.vector_store, self.document_store),
                        create_compare_tool(self.vector_store, self.document_store),
                        create_calculation_tool(),
                        create_extract_numbers_tool()
                    ]
                    
                    # Add stock tool
                    try:
                        from agents.tools.stock_tools import create_stock_tool
                        self._tools.append(create_stock_tool())
                    except ImportError as e:
                        print(f"Warning: Stock tool not available: {e}")
                    
                    # Add URL fetch tool (Docling-based, no storage)
                    try:
                        from agents.tools.url_tools import create_url_fetch_tool
                        self._tools.append(create_url_fetch_tool())
                    except ImportError as e:
                        print(f"Warning: URL fetch tool not available: {e}")
                        
                except ImportError as e:
                    print(f"Warning: Could not import agent tools: {e}")
        
        return self._tools
    
    def _get_agent_executor(self) -> Optional[AgentExecutor]:
        """Create AgentExecutor with tools and memory."""
        if self._agent_executor is None and self.tools:
            # Build system prompt
            system_prompt = self._get_agent_system_prompt()
            
            # Create prompt template with memory placeholder
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            try:
                # Create agent with tool calling
                agent = create_tool_calling_agent(self.llm, self.tools, prompt)
                
                self._agent_executor = AgentExecutor(
                    agent=agent,
                    tools=self.tools,
                    memory=self.memory,
                    verbose=True,
                    max_iterations=100,
                    handle_parsing_errors=True,
                    early_stopping_method="generate",
                    return_intermediate_steps=True  # Enable to debug tool usage
                )
            except Exception as e:
                print(f"Warning: Could not create AgentExecutor: {e}")
        
        return self._agent_executor
    
    def _get_agent_system_prompt(self) -> str:
        """Get system prompt for agent mode."""
        return """You are an expert financial document analyst with access to a document database.
You have conversation memory and can reference previous messages in our chat.

IMPORTANT: You have access to tools - USE THEM for every question about documents!

Available tools:
- search_documents: Search for relevant text across all documents and secondary sources (ALWAYS use this first!)
- get_document_content: Get full content from a specific document
- query_tables: Query structured table data (holdings, performance, etc.)
- compare_documents: Compare metrics across multiple documents
- calculate_metrics: Perform financial calculations
- extract_numbers: Extract numeric values from text
- get_stock_data: Fetch real-time stock market data (price, P/E, market cap, etc.)
  Use tickers like: AAPL, MSFT, 7203.T (Toyota), 6758.T (Sony)
- fetch_url_content: Fetch content from a URL on-the-fly using Docling (no storage)
  Use this when user provides a URL in their message and wants info from that page

CRITICAL WORKFLOW - Follow this for EVERY user question:
1. ALWAYS call search_documents first WITHOUT doc_id filter to find ALL relevant information
   (This searches BOTH primary documents AND secondary sources like attached URLs/files)
2. Review the search results - they include content from all attached sources
3. If user provides a URL in their message, use fetch_url_content to get its content
4. If user asks about stock prices or market data, use get_stock_data
5. If needed, use other tools for more detail
6. Provide a comprehensive answer based on the retrieved data

URL HANDLING:
- If user includes a URL (https://...) in their message, use fetch_url_content tool
- This fetches the page content instantly without storing it
- Perfect for quick lookups like "What does this page say about X? https://..."

IMPORTANT SEARCH TIPS:
- DO NOT pass doc_id parameter to search_documents unless user specifically asks about one document
- Secondary sources (URLs, attached files) are indexed and searchable
- Search broadly first, then narrow down if needed

NEVER say you don't have memory or can't help - you DO have tools and memory!
NEVER refuse to answer - always try searching first!

SMART PAGINATION RULE:
- Search results come in batches of up to 10
- After receiving results, EVALUATE: Do I have SUFFICIENT information to answer the user's question?
- If YES → Answer immediately (no need to fetch more)
- If NO or UNCERTAIN → Call search_documents again with skip=10, then skip=20, etc.
- Use your judgment: For specific questions (e.g., "What is the fund's expense ratio?"), one good match may be enough
- For broad questions (e.g., "Summarize all holdings"), fetch more results
- STOP fetching when you have enough information OR when you receive fewer than 10 results

Response format:
- Always base your answer on the search results
- Cite specific facts and numbers from the documents
- If no relevant data is found, say "I searched but couldn't find information about X"
- Be helpful and thorough"""
    
    def chat(self, message: str, doc_id: Optional[str] = None) -> str:
        """
        Chat with the agent about documents.
        Uses tools to search and retrieve information.
        """
        agent_executor = self._get_agent_executor()
        
        if not agent_executor:
            return "Agent not available. Please ensure vector store is configured."
        
        # Add document context to message if specified
        # NOTE: Don't filter by doc_id - let search find all relevant content including secondary sources
        if doc_id:
            message = f"[Current document ID for reference: {doc_id} - but search ALL content, don't filter by doc_id unless specifically needed]\n\n{message}"
        
        try:
            result = agent_executor.invoke({"input": message})
            
            # Debug: print the full result structure
            import logging
            logging.info(f"Agent result type: {type(result)}")
            logging.info(f"Agent result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
            logging.info(f"Agent result: {result}")
            
            # Get output, ensuring we have something to return
            output = result.get("output", "") if isinstance(result, dict) else str(result)
            
            # If output is empty but we have intermediate steps, try to extract something
            if not output and isinstance(result, dict):
                intermediate_steps = result.get("intermediate_steps", [])
                if intermediate_steps:
                    # Get the last tool response as fallback
                    last_step = intermediate_steps[-1]
                    if len(last_step) >= 2:
                        output = f"Based on the search results:\n\n{last_step[1]}"
            
            return output if output else "I couldn't generate a response. Please try rephrasing your question."
        except Exception as e:
            import traceback
            return f"Error: {str(e)}\n\n{traceback.format_exc()}"
    
    def clear_memory(self):
        """Clear conversation memory."""
        if self._memory:
            self._memory.clear()
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        if not self._memory:
            return []
        
        messages = self._memory.chat_memory.messages
        history = []
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        
        return history
    
    def generate(
        self, 
        data: ExtractedData, 
        params: CommentParameters,
        additional_context: Optional[str] = None
    ) -> str:
        """Generate comment based on extracted data and parameters."""
        
        # Build the data context
        data_context = self._build_data_context(data, params)
        
        # Add AI-analyzed context if provided
        if additional_context:
            data_context = f"{data_context}\n\n=== AI-ANALYZED CONTENT ===\n{additional_context}\n=== END AI-ANALYZED CONTENT ==="
        
        # Build the user prompt
        user_prompt = self._build_user_prompt(params, data_context)
        
        # Check if we have an agent executor with tools
        agent_executor = self._get_agent_executor()
        
        if agent_executor and self.tools:
            # Use agent with tools
            try:
                result = agent_executor.invoke({"input": user_prompt})
                return result.get("output", str(result))
            except Exception as e:
                print(f"Agent execution failed, falling back to chain: {e}")
                # Fallback to simple chain
                return self._generate_with_chain(params, data_context)
        else:
            # Use simple chain (original behavior)
            return self._generate_with_chain(params, data_context)
    
    def _generate_with_chain(self, params: CommentParameters, data_context: str) -> str:
        """Generate using simple chain (fallback mode)."""
        system_prompt = self._build_system_prompt(params)
        user_prompt = self._build_user_prompt(params, data_context)
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({})
    
    def _build_system_prompt(self, params: CommentParameters) -> str:
        """Build system prompt based on comment type."""
        
        base_prompt = """You are an expert financial writer specializing in asset management communications. 
Your task is to write professional fund commentary based STRICTLY on the provided data from the annual report.

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. ONLY use information that is explicitly present in the provided data
2. DO NOT invent or assume any company names, percentages, or events not in the data
3. DO NOT make up news events, stock price movements, or corporate actions
4. If specific details like contribution percentages are not provided, do not invent them
5. Use exact figures from the tables when available
6. If data is insufficient, acknowledge limitations rather than fabricating details
7. Every company name, every percentage, every fact MUST come from the provided document data

Key principles:
- Be factual and precise with numbers FROM THE DOCUMENT
- Provide context for performance figures USING DOCUMENT DATA
- Explain investment decisions based on WHAT THE DOCUMENT SHOWS
- Maintain consistent tone throughout
- Quote specific data points from tables when relevant
"""
        
        type_specific = {
            "asset_manager_comment": """
You are writing an Asset Manager Comment for a fund's official report. This should:
- Open with a brief market context
- Discuss fund performance vs benchmark
- Highlight key holdings and their contributions
- Explain any significant portfolio changes
- Provide a brief outlook
""",
            "performance_summary": """
You are writing a Performance Summary. This should:
- Focus primarily on quantitative performance data
- Compare fund returns to benchmark clearly
- Break down attribution by sector or holdings
- Be concise and data-driven
""",
            "risk_analysis": """
You are writing a Risk Analysis. This should:
- Discuss risk metrics and volatility
- Analyze drawdowns and recovery
- Compare risk-adjusted returns
- Highlight portfolio concentration risks
""",
            "sustainability_report": """
You are writing a Sustainability/ESG Report. This should:
- Focus on ESG metrics and scores
- Discuss sustainability initiatives
- Highlight green investments
- Report on carbon footprint if available
""",
            "newsletter_excerpt": """
You are writing a Newsletter Excerpt for retail investors. This should:
- Use accessible, jargon-free language
- Tell a compelling story about the fund
- Be engaging and easy to read
- Highlight key takeaways simply
""",
            "custom": """
You are writing a custom financial commentary. Follow the specific instructions provided carefully.
"""
        }
        
        tone_guidance = {
            "formal": "Use formal, professional language appropriate for institutional investors.",
            "conversational": "Use a friendly, conversational tone while maintaining professionalism.",
            "technical": "Use technical financial terminology appropriate for sophisticated investors."
        }
        
        length_guidance = {
            "brief": "Keep the response concise, around 100 words.",
            "medium": "Write a moderate-length response, around 200 words.",
            "detailed": "Write a comprehensive response, around 400 words with detailed analysis."
        }
        
        return f"""{base_prompt}

{type_specific.get(params.comment_type, type_specific["custom"])}

Tone: {tone_guidance.get(params.tone, tone_guidance["formal"])}
Length: {length_guidance.get(params.length, length_guidance["medium"])}
"""
    
    def _build_data_context(self, data: ExtractedData, params: CommentParameters) -> str:
        """Build structured data context for the prompt."""
        
        context_parts = []
        
        # Fund info
        if data.fund_name:
            context_parts.append(f"Fund Name: {data.fund_name}")
        if data.report_period:
            context_parts.append(f"Report Period: {data.report_period}")
        if data.benchmark_index and params.compare_benchmark:
            context_parts.append(f"Benchmark: {data.benchmark_index}")
        if data.currency:
            context_parts.append(f"Currency: {data.currency}")
        
        # Performance data
        if data.performance:
            perf = data.performance
            perf_lines = ["", "Performance Data:"]
            if perf.fund_return is not None:
                perf_lines.append(f"  Fund Return: {perf.fund_return:+.2f}%")
            if perf.benchmark_return is not None and params.compare_benchmark:
                perf_lines.append(f"  Benchmark Return: {perf.benchmark_return:+.2f}%")
            if perf.outperformance is not None and params.compare_benchmark:
                perf_lines.append(f"  Outperformance: {perf.outperformance:+.2f}%")
            if perf.period:
                perf_lines.append(f"  Period: {perf.period}")
            context_parts.extend(perf_lines)
        
        # Holdings
        if data.holdings and params.top_n_holdings > 0:
            top_holdings = data.holdings[:params.top_n_holdings]
            holdings_lines = ["", f"Top {len(top_holdings)} Holdings:"]
            for i, h in enumerate(top_holdings, 1):
                weight_str = f"{h.weight:.2f}%" if h.weight else "N/A"
                contrib_str = f", contribution: {h.contribution:+.2f}%" if h.contribution else ""
                sector_str = f" ({h.sector})" if h.sector else ""
                holdings_lines.append(f"  {i}. {h.name}{sector_str}: {weight_str}{contrib_str}")
            context_parts.extend(holdings_lines)
        
        # Sectors
        if data.sectors and params.include_sector_impact:
            sector_lines = ["", "Sector Allocation:"]
            for s in data.sectors[:8]:
                sector_lines.append(f"  {s.sector}: {s.weight:.1f}%")
            context_parts.extend(sector_lines)
        
        # RAW TABLES - Include all extracted tables
        if data.raw_tables:
            context_parts.append("\n\n=== RAW TABLES FROM DOCUMENT ===")
            for table in data.raw_tables[:10]:  # Limit to 10 tables
                context_parts.append(f"\nTable (Page {table.page}, Type: {table.table_type}):")
                if table.headers:
                    context_parts.append(f"  Headers: {' | '.join(table.headers)}")
                for row in table.rows[:15]:  # Limit rows per table
                    context_parts.append(f"  {' | '.join(str(cell) for cell in row)}")
            context_parts.append("=== END TABLES ===")
        
        # Chart descriptions
        if data.chart_descriptions:
            chart_lines = ["", "Charts Found:"]
            for desc in data.chart_descriptions[:5]:
                chart_lines.append(f"  - {desc}")
            context_parts.extend(chart_lines)
        
        # ALWAYS include raw text for context (larger excerpt)
        if data.raw_text:
            # Include more text - up to 8000 chars for better context
            excerpt = data.raw_text[:8000]
            context_parts.append(f"\n\n=== DOCUMENT TEXT ===\n{excerpt}\n=== END DOCUMENT TEXT ===")
        
        return "\n".join(context_parts)
    
    def _build_user_prompt(self, params: CommentParameters, data_context: str) -> str:
        """Build the user prompt."""
        
        prompt_parts = [
            "Based on the following fund data, please write the requested commentary.",
            "",
            "=== FUND DATA ===",
            data_context,
            "",
            "=== END DATA ==="
        ]
        
        if params.custom_instructions:
            prompt_parts.extend([
                "",
                "Additional Instructions:",
                params.custom_instructions
            ])
        
        if params.include_positive_contributors and params.include_negative_contributors:
            prompt_parts.append("\nPlease discuss both positive and negative contributors to performance.")
        elif params.include_positive_contributors:
            prompt_parts.append("\nFocus primarily on positive contributors to performance.")
        elif params.include_negative_contributors:
            prompt_parts.append("\nDiscuss the negative contributors to performance.")
        
        prompt_parts.append("\nPlease generate the commentary now:")
        
        return "\n".join(prompt_parts)
    
    async def generate_async(
        self, 
        data: ExtractedData, 
        params: CommentParameters
    ) -> str:
        """Async version of generate."""
        return self.generate(data, params)
