with open(r"d:\Projects\Github\Market Digest\.design-pkg\market-digest\project\Market Digest.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("File total lines:", len(lines))

keywords = ["heatmap", "tradingview", "chart", "widget", "iframe"]
for i, line in enumerate(lines):
    for kw in keywords:
        if kw in line.lower():
            # Print line number and the line content (truncated)
            print(f"L{i+1} ({kw}): {line.strip()[:140]}")
            break
