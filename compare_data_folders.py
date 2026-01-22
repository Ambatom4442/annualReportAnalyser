from src.storage.document_store import DocumentStore

print("=" * 60)
print("COMPARING TWO .data FOLDERS")
print("=" * 60)

# Check ROOT .data
print("\n1. ROOT .data (D:\\Sweden\\annualReportAnalyser\\.data):")
ds_root = DocumentStore(".data")
docs_root = ds_root.list_documents()
print(f"   Documents: {len(docs_root)}")
for d in docs_root:
    print(f"   - {d['filename']} (ID: {d['id']})")

# Check SRC .data
print("\n2. SRC .data (D:\\Sweden\\annualReportAnalyser\\src\\.data):")
ds_src = DocumentStore("src/.data")
docs_src = ds_src.list_documents()
print(f"   Documents: {len(docs_src)}")
for d in docs_src:
    print(f"   - {d['filename']} (ID: {d['id']})")

print("\n" + "=" * 60)
print(f"RESULT: Your document is in the {'SRC' if len(docs_src) > 0 else 'ROOT'} .data folder")
print("=" * 60)
