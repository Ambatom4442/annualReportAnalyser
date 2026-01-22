"""Debug secondary source chunks."""
import chromadb

client = chromadb.PersistentClient(path=r'D:\Sweden\annualReportAnalyser\src\.data\chromadb')
collection = client.get_collection('annual_reports')

# Get all chunks and find asset manager comment
results = collection.get(limit=200, include=['documents', 'metadatas'])
print(f'Total chunks: {len(results["ids"])}')

# Search for manager commentary keywords
keywords = ['manager', 'comment', 'outperformed', 'benchmark']
for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
    doc_lower = doc.lower()
    if 'outperformed' in doc_lower or 'benchmark index' in doc_lower:
        doc_id = meta.get('doc_id', 'unknown')
        source_type = meta.get('source_type', 'primary')
        print(f'\nFound commentary in chunk {i}:')
        print(f'  doc_id: {doc_id}')
        print(f'  source_type: {source_type}')
        print(f'  Content:\n{doc[:800]}')
        print('\n---')
