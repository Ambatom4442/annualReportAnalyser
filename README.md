# 📊 Annual Report Analyser

AI-powered tool for generating Asset Manager Comments from fund annual reports.

## Features

- **PDF Upload**: Upload annual reports (up to 20 pages)
- **Intelligent Extraction**: Automatically extracts text, tables, images, and metadata
- **Dynamic UI**: Adapts parameter options based on detected content
- **AI-Powered Generation**: Uses Google Gemini to generate professional comments
- **Multiple Comment Types**: Asset Manager Comment, Performance Summary, Risk Analysis, etc.
- **Export Options**: Copy, download as TXT, MD, HTML, or JSON

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure API Key

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
```

Get your API key at: https://aistudio.google.com/app/apikey

### 3. Run the App

```bash
uv run streamlit run src/app.py
```

The app will open at http://localhost:8501

## Usage

1. **Upload** a fund annual report PDF (max 20 pages)
2. **Review** the extracted content summary
3. **Configure** your comment parameters:
   - Comment type (Asset Manager Comment, Performance Summary, etc.)
   - Tone (Formal, Conversational, Technical)
   - Length (Brief, Medium, Detailed)
   - Content options (holdings, sectors, benchmarks)
4. **Generate** the AI-powered comment
5. **Edit** and **Export** in your preferred format

## Tech Stack

- **UI**: Streamlit
- **PDF Processing**: pdfplumber, PyMuPDF
- **AI**: LangChain + Google Gemini 1.5 Pro
- **Data Validation**: Pydantic

## Project Structure

```
src/
├── app.py                 # Main Streamlit app
├── config.py              # Configuration
├── extractors/            # PDF extraction modules
│   ├── text_extractor.py
│   ├── table_extractor.py
│   ├── image_extractor.py
│   └── metadata_extractor.py
├── models/                # Pydantic data models
│   ├── extracted_data.py
│   └── comment_params.py
├── agents/                # LangChain agent
│   └── comment_agent.py
└── ui/                    # UI components
    ├── upload_component.py
    ├── parameter_ui.py
    └── preview_component.py
```

## License

MIT