"""Verify secondary source processing."""
import sqlite3
import chromadb

# Check SQLite
print("=== SQLite Secondary Sources ===")
conn = sqlite3.connect(r'D:\Sweden\annualReportAnalyser\src\.data\secondary_sources.db')
c = conn.cursor()
c.execute('SELECT source_id, name, source_type, is_processed, chunk_count, parent_doc_id FROM secondary_sources')
for row in c.fetchall():
    print(f"  ID: {row[0]}")
    print(f"  Name: {row[1]}")
    print(f"  Type: {row[2]}")
    print(f"  Processed: {row[3]}")
    print(f"  Chunks: {row[4]}")
    print(f"  Parent Doc: {row[5]}")
    print()
conn.close()

# Check ChromaDB for secondary chunks
print("=== ChromaDB Secondary Chunks ===")
client = chromadb.PersistentClient(path=r'D:\Sweden\annualReportAnalyser\src\.data\chromadb')
collection = client.get_collection('annual_reports')

results = collection.get(where={'source_type': 'secondary'}, limit=200, include=['documents', 'metadatas'])
print(f"Total secondary chunks: {len(results['ids'])}")

# Check for Takeda/Sony content
takeda_found = False
sony_found = False
peanuts_found = False
psoriasis_found = False

for doc in results['documents']:
    if 'Takeda' in doc:
        takeda_found = True
    if 'Sony' in doc:
        sony_found = True
    if 'Peanuts' in doc or 'peanuts' in doc.lower():
        peanuts_found = True
    if 'psoriasis' in doc.lower():
        psoriasis_found = True

print(f"\nContent verification:")
print(f"  Contains 'Takeda': {takeda_found}")
print(f"  Contains 'Sony': {sony_found}")
print(f"  Contains 'Peanuts': {peanuts_found}")
print(f"  Contains 'psoriasis': {psoriasis_found}")

if takeda_found and sony_found:
    print("\n✅ SUCCESS: Dynamic content (Asset Manager Comment) was extracted!")
else:
    print("\n❌ ISSUE: Dynamic content may not have been extracted properly")
