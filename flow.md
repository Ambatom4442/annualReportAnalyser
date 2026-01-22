# Annual Report Analyser - Complete Flow

## Overview
A Streamlit app that takes a fund's annual report PDF and generates AI-powered Asset Manager Comments using dynamic content discovery.

---

## **Step 1: PDF Upload** (`src/app.py` lines 95-105)

```
User uploads PDF → Validates (≤20 pages) → Stores in session state
```

- User uploads a fund annual report PDF
- `src/ui/upload_component.py` validates file size and page count
- PDF bytes stored in `st.session_state.pdf_data`

---

## **Step 2: AI Document Analysis** (`src/app.py` lines 108-165)

This is the **new dynamic analysis** step with 3 parallel processes:

### 2a. Basic Extraction
```
PDF → TextExtractor → raw_text
PDF → TableExtractor → raw_tables (headers, rows, types)
PDF → MetadataExtractor → fund_name, period, benchmark
```

### 2b. Document Analyzer Agent (`src/agents/document_analyzer.py`)
```
raw_text + tables → Gemini AI → Structured JSON
```

Returns:
```json
{
  "fund_info": { "name", "benchmark", "period", "currency" },
  "sections": [ { "title", "type", "summary" } ],
  "tables": [ { "title", "type", "key_data", "row_count" } ],
  "charts": [ { "title", "type", "description" } ],
  "companies": [ { "name", "context": "positive/negative/holding" } ],
  "metrics": [ { "name", "value", "category" } ],
  "themes": [ { "name", "relevance", "description" } ],
  "key_insights": [ "..." ]
}
```

### 2c. Chart Vision Analysis
```
PDF → ImageExtractor → chart images → Gemini Vision → chart descriptions
```

Each chart analyzed for: type, data points, trends, labels

---

## **Step 3: Dynamic Content Selection UI** (`src/ui/dynamic_parameter_ui.py`)

User sees **6 tabs** with AI-discovered content:

| Tab | Content | Selection Type |
|-----|---------|----------------|
| 📑 Sections | Document sections (Performance, Holdings, etc.) | Checkboxes |
| 📊 Tables | All tables with preview | Checkboxes + data preview |
| 📈 Charts | Chart images with AI descriptions | Image cards + checkboxes |
| 🏢 Companies | Grouped by context (positive/negative/holdings) | Multi-select |
| 📉 Metrics | Grouped by category (performance/risk/fees) | Checkboxes |
| 🎯 Themes | ESG, Technology, etc. with relevance | Checkboxes |

Plus configuration:
- **Comment Type**: Asset Manager, Performance Summary, Risk Analysis, etc.
- **Tone**: Formal / Conversational / Technical
- **Length**: Brief / Medium / Detailed
- **Custom Instructions**: User's specific requirements (mandatory field)

---

## **Step 4: Comment Generation** (`src/agents/comment_agent.py`)

```
User selections → _build_context_from_selections() → context string
context + extracted_data + params → CommentGeneratorAgent → Gemini → Comment
```

The agent receives:
1. **Raw document data**: Full text, all tables, chart descriptions
2. **AI-analyzed selections**: Only the content user selected in Step 3
3. **Parameters**: Comment type, tone, length, custom instructions

**Critical rules enforced**:
- Only use information explicitly in the document
- No invented company names, percentages, or events
- Exact figures from tables when available

---

## **Step 5: Preview & Export** (`src/ui/preview_component.py`)

```
Generated comment → Editable text area → Export options
```

- Edit the generated comment
- Regenerate with different selections
- Export as TXT, MD, or JSON

---

## **Data Flow Diagram**

```
┌─────────────┐
│  PDF Upload │
└──────┬──────┘
       ▼
┌──────────────────────────────────────────────────────┐
│              STEP 2: AI ANALYSIS                      │
├──────────────┬──────────────────┬────────────────────┤
│ TextExtractor│ DocumentAnalyzer │ ChartVision        │
│ TableExtractor│ Agent (Gemini)  │ (Gemini)           │
│ MetadataExtr │                  │                    │
└──────┬───────┴────────┬─────────┴──────────┬─────────┘
       │                │                    │
       ▼                ▼                    ▼
   raw_text      document_analysis     analyzed_charts
   raw_tables    (structured JSON)     (with images)
       │                │                    │
       └────────────────┼────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────┐
│           STEP 3: DYNAMIC UI                          │
│  [Sections] [Tables] [Charts] [Companies] [Metrics]   │
│                 User selects content                  │
│            + Comment type, tone, length               │
│            + Custom instructions                      │
└───────────────────────┬───────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────┐
│           STEP 4: GENERATION                          │
│  CommentGeneratorAgent (LangChain + Gemini)           │
│  - System prompt with strict rules                    │
│  - User-selected context                              │
│  - Raw data for verification                          │
└───────────────────────┬───────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────┐
│           STEP 5: PREVIEW & EXPORT                    │
│  Edit → TXT / MD / JSON                               │
└───────────────────────────────────────────────────────┘
```

---

## **Key Files**

| File | Purpose |
|------|---------|
| `src/app.py` | Main orchestrator |
| `src/agents/document_analyzer.py` | AI content discovery |
| `src/agents/comment_agent.py` | Comment generation |
| `src/agents/chart_analyzer.py` | Vision analysis |
| `src/ui/dynamic_parameter_ui.py` | Selection UI |
| `src/ui/upload_component.py` | PDF upload |
| `src/ui/preview_component.py` | Preview & export |
| `src/extractors/text_extractor.py` | PDF text extraction |
| `src/extractors/table_extractor.py` | PDF table extraction |
| `src/extractors/image_extractor.py` | PDF image/chart extraction |
| `src/extractors/metadata_extractor.py` | Fund metadata extraction |
| `src/models/extracted_data.py` | Pydantic data models |
| `src/models/comment_params.py` | Comment parameters model |
| `src/config.py` | Configuration (API keys, settings) |

---

## **Tech Stack**

- **UI**: Streamlit
- **PDF Processing**: pdfplumber, PyMuPDF (fitz)
- **AI/LLM**: LangChain + Google Gemini (`google-genai`)
- **Vision**: Gemini 2.0 Flash for chart analysis
- **Data Validation**: Pydantic
- **Package Manager**: UV