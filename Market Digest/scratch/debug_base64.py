import base64
from pathlib import Path

# Test base64 conversion
def get_base64_img(path: Path) -> str:
    if not path.exists():
        return "PATH_DOES_NOT_EXIST"
    try:
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif suffix == ".png":
            mime = "image/png"
        else:
            mime = "image/png"
            
        with open(path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{encoded[:50]}... (len={len(encoded)})"
    except Exception as e:
        return f"ERROR: {e}"

# Check files
paths = [
    Path("C:/Users/K964/OneDrive - Shriram Finance Limited/Desktop/logo.png"),
    Path("d:/Projects/Github/Market Digest/market_digest/logo.jpeg"),
    Path("d:/Projects/Github/Market Digest/market_digest/logo.png"),
    Path("d:/Projects/Github/Market Digest/market_digest/bull_bear_banner.png")
]

for p in paths:
    print(f"{p}: {get_base64_img(p)}")

# Check generated html content
card_file = Path("d:/Projects/Github/Market Digest/output/card_indices.html")
if card_file.exists():
    text = card_file.read_text(encoding="utf-8")
    import re
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', text)
    print("Found images in card_indices.html:")
    for idx, img in enumerate(imgs):
        print(f"  Img {idx}: {img[:80]}... (len={len(img)})")
else:
    print("card_indices.html does not exist!")
