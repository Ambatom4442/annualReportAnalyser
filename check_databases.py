from src.storage.document_store import DocumentStore
from src.storage.chat_store import ChatStore
import chromadb
import os
from pathlib import Path

print('='*60)
print('CHECKING ALL DATABASES')
print('='*60)

# 1. Documents Database
print('\n1. DOCUMENT DATABASE (documents.db):')
ds = DocumentStore()
docs = ds.list_documents()
print(f'   Total documents: {len(docs)}')
if docs:
    for d in docs:
        print(f'   - ID: {d["id"]}, File: {d["filename"]}')

# 2. Chat/Secondary Sources Database
print('\n2. CHAT DATABASE (chat_history.db):')
data_dir = Path('.data')
cs = ChatStore(str(data_dir / "chat_history.db"))

# Query database directly
import sqlite3
with sqlite3.connect(data_dir / "chat_history.db") as conn:
    # List all tables
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print(f'   Tables: {tables}')

    # Count chat history
    cursor = conn.execute('SELECT COUNT(*) FROM chat_history')
    chat_count = cursor.fetchone()[0]
    print(f'   Chat messages: {chat_count}')

    # Count research summaries
    cursor = conn.execute('SELECT COUNT(*) FROM research_summaries')
    summary_count = cursor.fetchone()[0]
    print(f'   Research summaries: {summary_count}')

    # Show recent summaries if any
    if summary_count > 0:
        cursor = conn.execute('SELECT id, title, created_at FROM research_summaries ORDER BY created_at DESC LIMIT 5')
        print('   Recent summaries:')
        for row in cursor.fetchall():
            print(f'     - ID: {row[0]}, Title: "{row[1]}", Created: {row[2]}')

# 3. ChromaDB
print('\n3. CHROMADB (.data/chromadb):')
try:
    chroma_path = os.path.join('.data', 'chromadb')
    if os.path.exists(chroma_path):
        client = chromadb.PersistentClient(path=chroma_path)
        collections = client.list_collections()
        print(f'   Total collections: {len(collections)}')
        for col in collections:
            count = col.count()
            print(f'   - Collection: "{col.name}", Vectors: {count}')
    else:
        print('   ChromaDB directory does not exist')
except Exception as e:
    print(f'   Error accessing ChromaDB: {e}')

# 4. Cached Files
print('\n4. CACHED FILES (.data/cache):')
cache_dir = '.data/cache'
if os.path.exists(cache_dir):
    files = [f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))]
    print(f'   Cached files: {len(files)}')
    if files:
        for f in files[:10]:  # Show first 10
            size = os.path.getsize(os.path.join(cache_dir, f))
            print(f'   - {f} ({size} bytes)')
else:
    print('   No cache directory found')

# 5. Uploaded Files
print('\n5. UPLOADED FILES (.data/files):')
files_dir = '.data/files'
if os.path.exists(files_dir):
    all_files = []
    for root, dirs, files in os.walk(files_dir):
        for f in files:
            full_path = os.path.join(root, f)
            size = os.path.getsize(full_path)
            all_files.append((f, size))
    print(f'   Total files: {len(all_files)}')
    for f, size in all_files[:10]:
        print(f'   - {f} ({size} bytes)')
else:
    print('   No files directory found')

print('\n' + '='*60)
print('DATABASE CHECK COMPLETE')
print('='*60)
