import fitz
doc = fitz.open(r"d:\Projects\Github\Market Digest\StonkzzReport-30Sep.pdf")
print("Number of pages:", len(doc))
for i in range(min(5, len(doc))):
    print(f"\n--- Page {i+1} Text ---")
    text = doc[i].get_text()
    print(text[:1500])
doc.close()
