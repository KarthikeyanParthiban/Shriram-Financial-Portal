import fitz
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
out = BASE_DIR / "output" / "ref_pages"
out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(str(BASE_DIR / "StonkzzReport-30Sep.pdf"))
print(f"Reference Pages: {len(doc)}")
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    pix.save(out / f"page_{i+1:02d}.png")
    print(f"Page {i+1}: {page.rect}  -> {pix.width}x{pix.height}")
doc.close()
