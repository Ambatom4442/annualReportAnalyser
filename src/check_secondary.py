"""Quick check of ChromaDB secondary sources."""
import chromadb

client = chromadb.PersistentClient(path="D:/Sweden/annualReportAnalyser/src/.data/chromadb")
col = client.get_collection("annual_reports")
data = col.get(include=["metadatas"])

total = len(data["ids"])
secondary = [m for m in data["metadatas"] if m.get("source_type") == "secondary"]

print(f"Total chunks: {total}")
print(f"Secondary chunks: {len(secondary)}")

if secondary:
    print("\nSample secondary metadata:")
    print(secondary[0])
