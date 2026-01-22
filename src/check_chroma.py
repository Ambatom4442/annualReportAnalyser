"""Check ChromaDB data for secondary sources."""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from storage.vector_store import VectorStore

# Test semantic search with the agent's query
query = "asset manager comments Sony Takeda"
print(f"=== Query: '{query}' ===\n")

vs = VectorStore(api_key=os.getenv("GOOGLE_API_KEY"))
results = vs.search(query, n_results=15)

print(f"Found {len(results)} results:\n")
for i, r in enumerate(results):
    source_type = r['metadata'].get('source_type', 'primary')
    doc_id = r['metadata'].get('doc_id', '?')[:30]
    content = r['content'][:100].replace('\n', ' ')
    print(f"{i+1}. [{source_type}] {content}...")

# Check for secondary sources
secondary_chunks = []
primary_doc_ids = set()

for i, meta in enumerate(all_data["metadatas"]):
    if meta.get("source_type") == "secondary":
        secondary_chunks.append({
            "id": all_data["ids"][i],
            "doc_id": meta.get("doc_id"),
            "source_id": meta.get("source_id"),
            "source_name": meta.get("source_name"),
            "content_preview": all_data["documents"][i][:150] if all_data["documents"][i] else "N/A"
        })
    else:
        primary_doc_ids.add(meta.get("doc_id"))

print(f"\nPrimary doc chunks: {len(all_data['metadatas']) - len(secondary_chunks)}")
print(f"Unique primary doc_ids: {primary_doc_ids}")
print(f"\nSecondary source chunks: {len(secondary_chunks)}")

if secondary_chunks:
    print("\n--- Secondary Source Chunks ---")
    for chunk in secondary_chunks[:5]:
        print(f"ID: {chunk['id']}")
        print(f"  doc_id: {chunk['doc_id']}")
        print(f"  source_id: {chunk['source_id']}")
        print(f"  source_name: {chunk['source_name']}")
        print(f"  content: {chunk['content_preview']}...")
        print()
else:
    print("\nNo secondary source chunks found in ChromaDB!")
