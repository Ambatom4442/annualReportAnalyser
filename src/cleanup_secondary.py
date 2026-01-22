"""Clean up and test secondary source extraction."""
import chromadb
import sqlite3

# Delete all secondary chunks from ChromaDB
client = chromadb.PersistentClient(path=r'D:\Sweden\annualReportAnalyser\src\.data\chromadb')
collection = client.get_collection('annual_reports')

results = collection.get(where={'source_type': 'secondary'}, include=[])
chunk_count = len(results["ids"])
print(f'Found {chunk_count} secondary chunks to delete')

if results['ids']:
    collection.delete(ids=results['ids'])
    print('Deleted secondary chunks from ChromaDB')

# Delete secondary sources from SQLite
conn = sqlite3.connect(r'D:\Sweden\annualReportAnalyser\src\.data\secondary_sources.db')
c = conn.cursor()
c.execute('DELETE FROM secondary_sources')
conn.commit()
print('Deleted secondary sources from SQLite')
conn.close()

print('\nCleanup complete. Re-attach the URL in the app to test new extraction.')
