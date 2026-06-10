"""Publish generated mobile cards to Microsoft Teams via webhooks."""
from __future__ import annotations

import base64
from pathlib import Path
import requests


def publish_to_teams(webhook_url: str, output_dir: Path) -> tuple[bool, str]:
    """Base64-encode the generated PNG cards and send them to the Microsoft Teams webhook."""
    if not webhook_url:
        return False, "Webhook URL is empty."
        
    indices_png = output_dir / "card_indices.png"
    news_png = output_dir / "card_news.png"
    
    if not indices_png.exists() or not news_png.exists():
        return False, "Generated card PNG files not found. Generate them first."
        
    try:
        # Base64 encode the PNG files
        with open(indices_png, "rb") as f:
            indices_b64 = base64.b64encode(f.read()).decode("utf-8")
        with open(news_png, "rb") as f:
            news_b64 = base64.b64encode(f.read()).decode("utf-8")
            
        # Standard Connector MessageCard payload containing both images stacked
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "F7B500",
            "summary": "SAMC Micro Digest - Daily News & Update",
            "sections": [
                {
                    "activityTitle": "SAMC Micro Digest - Indices & News",
                    "activitySubtitle": "Mobile-friendly daily update cards",
                    "text": "Here are today's daily infographics:",
                    "images": [
                        {
                            "image": f"data:image/png;base64,{indices_b64}"
                        },
                        {
                            "image": f"data:image/png;base64,{news_b64}"
                        }
                    ]
                }
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        r = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
        
        if r.status_code in (200, 201, 202):
            return True, "Published successfully!"
        else:
            return False, f"HTTP Error {r.status_code}: {r.text}"
            
    except Exception as e:
        return False, f"Exception during publish: {e}"
