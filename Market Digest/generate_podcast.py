import os
import sys
import asyncio
import re
import uuid
import shutil
import ssl
from datetime import datetime
import edge_tts
import aiohttp

# Monkey-patch aiohttp to globally disable SSL verification for corporate proxy environments
original_request = aiohttp.ClientSession._request
async def patched_request(self, *args, **kwargs):
    kwargs['ssl'] = False
    return await original_request(self, *args, **kwargs)
aiohttp.ClientSession._request = patched_request

# Add project root to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from market_digest.fetch import fetch_all

# Voice and Rate configurations (Updated to standard natural US neural voices)
VOICE_ARJUN = "en-US-GuyNeural"
RATE_ARJUN = "-2%"

VOICE_NEHA = "en-US-JennyNeural"
RATE_NEHA = "-2%"

def number_to_words(num):
    if num == 0:
        return "zero"
    units = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", 
             "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    
    def _helper(n):
        if n < 20:
            return units[n]
        elif n < 100:
            t = tens[n // 10]
            u = units[n % 10]
            return f"{t}-{u}" if u else t
        elif n < 1000:
            h = units[n // 100]
            r = _helper(n % 100)
            return f"{h} hundred and {r}" if r else f"{h} hundred"
        elif n < 1000000:
            th = _helper(n // 1000)
            r = _helper(n % 1000)
            if r:
                sep = " and " if (n % 1000) < 100 else " "
                return f"{th} thousand{sep}{r}"
            return f"{th} thousand"
        elif n < 1000000000:
            m = _helper(n // 1000000)
            r = _helper(n % 1000000)
            if r:
                sep = " and " if (n % 1000000) < 100 else " "
                return f"{m} million{sep}{r}"
            return f"{m} million"
        else:
            b = _helper(n // 1000000000)
            r = _helper(n % 1000000000)
            if r:
                sep = " and " if (n % 1000000000) < 100 else " "
                return f"{b} billion{sep}{r}"
            return f"{b} billion"
            
    return _helper(int(num)).strip()

def speak_number(val, speak_sign=False):
    """Convert integer or float string into clean, spoken English words."""
    try:
        val_str = str(val).replace(",", "").strip()
        if not val_str:
            return ""
        
        is_negative = val_str.startswith("-")
        is_positive = val_str.startswith("+")
        
        clean_str = val_str
        if is_negative or is_positive:
            clean_str = val_str[1:]
            
        if "." in clean_str:
            parts = clean_str.split(".")
            integer_part = int(parts[0]) if parts[0] else 0
            decimal_part = parts[1]
            
            # Convert decimal part to digit names
            digits_map = {
                "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", 
                "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"
            }
            decimal_text = " point " + " ".join(digits_map[d] for d in decimal_part if d in digits_map)
        else:
            integer_part = int(clean_str)
            decimal_text = ""
            
        words = (number_to_words(integer_part) + decimal_text).strip()
        
        if is_negative:
            return "minus " + words
        elif is_positive and speak_sign:
            return "plus " + words
        return words
    except Exception as e:
        print(f"Error converting number {val} to words: {e}")
        return str(val)

async def generate_turn(text: str, voice: str, filename: str, rate: str = "+0%"):
    """Generate audio for a single dialogue turn using edge-tts."""
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(filename)
        return True
    except Exception as e:
        print(f"Error generating TTS for turn: {e}")
        return False

def clean_currency(value):
    """Remove currency symbols and format text for smooth TTS pronunciation."""
    if not value:
        return "Not available"
    val_str = str(value)
    val_str = val_str.replace("₹", "Rupees ")
    val_str = val_str.replace("Rs.", "Rupees ")
    val_str = val_str.replace('"', '').replace("'", "")
    return val_str

async def main():
    print("Market Digest Podcast Generator starting...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    project_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(project_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    podcast_mp3_path = os.path.join(output_dir, "podcast.mp3")
    
    # 1. Fetch market data
    print("Fetching latest market data for podcast script...")
    try:
        data = fetch_all()
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)
        
    # Extract metrics safely with correct keys
    nifty = data.get("nifty") or {}
    if nifty.get("available") and nifty.get("close") is not None:
        nifty_close = nifty["close"]
        nifty_chg = nifty.get("change", 0.0)
        nifty_chg_pct = nifty.get("change_pct", 0.0)
        
        nifty_close_str = speak_number(f"{nifty_close:.2f}")
        nifty_chg_str = speak_number(f"{nifty_chg:+.2f}", speak_sign=True)
        nifty_chg_pct_str = speak_number(f"{nifty_chg_pct:+.2f}", speak_sign=True)
        
        nifty_text = f"{nifty_close_str}, which is a change of {nifty_chg_str} points, or {nifty_chg_pct_str} percent"
    else:
        nifty_text = "unavailable at the moment"
    
    sentiment = data.get("sentiment") or {}
    sentiment_score = sentiment.get("score")
    if sentiment_score is not None:
        sentiment_score_str = speak_number(sentiment_score)
    else:
        sentiment_score_str = "Not available"
    sentiment_label = sentiment.get("label", "Neutral")
    
    mmi = data.get("mmi") or {}
    mmi_val = mmi.get("current", 50.0)
    mmi_val_str = speak_number(f"{mmi_val:.1f}")
    mmi_zone = mmi.get("zone", "Neutral")
    
    vix = data.get("vix") or {}
    if vix.get("available") and vix.get("value") is not None:
        vix_val_str = speak_number(f"{vix['value']:.2f}")
        vix_chg_pct_str = speak_number(f"{vix.get('change_pct', 0.0):+.2f}", speak_sign=True)
        vix_text = f"{vix_val_str}, representing a change of {vix_chg_pct_str} percent"
    else:
        vix_text = "not available"
    
    fii_dii = data.get("fii_dii") or {}
    fii_text = "neutral flows"
    dii_text = "neutral flows"
    if fii_dii.get("available") and fii_dii.get("rows"):
        latest = fii_dii["rows"][0]
        fii_val = latest.get("fii", 0.0)
        dii_val = latest.get("dii", 0.0)
        fii_abs_str = speak_number(f"{abs(fii_val):.1f}")
        dii_abs_str = speak_number(f"{abs(dii_val):.1f}")
        fii_text = f"a net outflow of {fii_abs_str} Crores" if fii_val < 0 else f"a net inflow of {fii_abs_str} Crores"
        dii_text = f"a net outflow of {dii_abs_str} Crores" if dii_val < 0 else f"a net inflow of {dii_abs_str} Crores"
    
    gold = data.get("gold") or {}
    if gold.get("available") and gold.get("today_24") and gold["today_24"].get("g10") is not None:
        gold_val_str = speak_number(f"{gold['today_24']['g10']:.0f}")
        gold_val = f"{gold_val_str} Rupees per ten grams"
    else:
        gold_val = "not available"

    silver = data.get("silver") or {}
    if silver.get("available") and silver.get("today") and silver["today"].get("kg1") is not None:
        silver_val_str = speak_number(f"{silver['today']['kg1']:.0f}")
        silver_val = f"{silver_val_str} Rupees per kilogram"
    else:
        silver_val = "not available"
    
    # Get top 2 news headlines
    news_data = data.get("news") or {}
    news_items = news_data.get("headlines") or []
    news_headlines = []
    for title in news_items[:2]:
        if title:
            title = title.replace('"', '').replace("'", "")
            news_headlines.append(title)
            
    while len(news_headlines) < 2:
        news_headlines.append("No major corporate news updates reported.")

    # 2. Build the dialogue script (Polished for natural phrasing & South Indian English politeness/precision)
    dialogue = [
        (VOICE_ARJUN, RATE_ARJUN, "Arjun", "Welcome to today's Market Digest audio briefing. I am Arjun."),
        (VOICE_NEHA, RATE_NEHA, "Neha", f"And I am Neha. Let's look at the numbers. Arjun, the overall market sentiment score stands at {sentiment_score_str} percent today, putting us in the '{sentiment_label}' category."),
        (VOICE_ARJUN, RATE_ARJUN, "Arjun", f"Yes, Neha, and the Market Mood Index is currently reading {mmi_val_str}, placing us in the '{mmi_zone}' zone. This suggests that while momentum is steady, greed is in an elevated zone, so a bit of caution makes sense."),
        (VOICE_NEHA, RATE_NEHA, "Neha", f"Indeed. Volatility has also cooled down slightly, with the India VIX at {vix_text}. This is generally supportive of stability in the Nifty fifty, which closed at {nifty_text}."),
        (VOICE_ARJUN, RATE_ARJUN, "Arjun", f"On the commodities front, we see gold trading at {gold_val}, while silver is valued at {silver_val} in Chennai."),
        (VOICE_NEHA, RATE_NEHA, "Neha", f"Turning to institutional flows, Foreign Institutional Investors registered {fii_text}, while domestic institutions supported the market with DII net flows of {dii_text}."),
        (VOICE_ARJUN, RATE_ARJUN, "Arjun", f"For today's corporate triggers, the major headlines are: first, {news_headlines[0]}. And second, {news_headlines[1]}."),
        (VOICE_NEHA, RATE_NEHA, "Neha", "That wraps up our quick market digest briefing. Keep these key levels and news triggers in mind for your trading day."),
        (VOICE_ARJUN, RATE_ARJUN, "Arjun", "Have a productive trading session, everyone!")
    ]

    # 3. Generate individual turn audios
    temp_files = []
    print("Generating audio for dialogue script...")
    for idx, (voice, rate, speaker, text) in enumerate(dialogue):
        temp_file = os.path.join(output_dir, f"temp_turn_{idx}.mp3")
        print(f"  [{speaker}] (rate={rate}) {text[:50]}...")
        success = await generate_turn(text, voice, temp_file, rate=rate)
        if success:
            temp_files.append(temp_file)
        else:
            print("Failed to generate dialogue turn. Exiting.")
            # Cleanup already generated files
            for f in temp_files:
                if os.path.exists(f): os.remove(f)
            sys.exit(1)

    # 4. Concatenate temporary MP3 files into final podcast MP3
    print("Concatenating audio files into final podcast.mp3...")
    try:
        with open(podcast_mp3_path, "wb") as outfile:
            for f in temp_files:
                with open(f, "rb") as infile:
                    outfile.write(infile.read())
        print(f"Podcast compiled successfully at: {podcast_mp3_path}")
    except Exception as e:
        print(f"Error concatenating audio files: {e}")
        sys.exit(1)
    finally:
        # Cleanup temporary files
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
                
    print("Podcast generation process completed!")

if __name__ == "__main__":
    asyncio.run(main())
