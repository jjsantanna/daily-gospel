#!/usr/bin/env python3
"""
send_gospel.py — Self-contained daily gospel sender.
Fetches today's Catholic gospel, generates a reflection via Ollama,
and sends it to Telegram. No OpenClaw agent/tools needed.

Usage:
    python3 send_gospel.py

Config (config.json in same directory — never commit this file):
    {
      "telegram_token": "your_bot_token",
      "telegram_chat_id": "your_chat_id",
      "ollama_host": "http://localhost:11434",  (optional)
      "ollama_model": "gemma3:4b"               (optional)
    }

Env vars override config file:
    OLLAMA_HOST, OLLAMA_MODEL, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""

import json
import os
import sys
import urllib.request
import urllib.parse

# ── Config ────────────────────────────────────────────────────────────────────
_config_path = os.path.join(os.path.dirname(__file__), "config.json")
_config = {}
if os.path.exists(_config_path):
    with open(_config_path) as _f:
        _config = json.load(_f)

OLLAMA_HOST    = os.environ.get("OLLAMA_HOST",       _config.get("ollama_host",    "http://localhost:11434"))
OLLAMA_MODEL   = os.environ.get("OLLAMA_MODEL",      _config.get("ollama_model",   "gemma3:4b"))
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN",    _config.get("telegram_token", ""))
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT_ID",  _config.get("telegram_chat_id", ""))

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
    print("❌ Telegram token/chat_id not configured.\n"
          "   Create config.json (see config.example.json) or set env vars.", file=sys.stderr)
    sys.exit(1)


# ── 1. Fetch gospel ───────────────────────────────────────────────────────────
def fetch_gospel():
    """Reuse fetch_gospel.py logic inline."""
    import re
    url = "https://universalis.com/today/mass.htm"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None, f"Could not fetch gospel: {e}"

    m = re.search(
        r'Gospel(.*?)(?=<h[23]|Communion|Reflection|Prayer after Communion|$)',
        html, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return None, "Gospel section not found on Universalis."

    raw = m.group(1)
    raw = raw.replace('&#8216;', '\u2018').replace('&#8217;', '\u2019') \
             .replace('&#8220;', '\u201c').replace('&#8221;', '\u201d') \
             .replace('&amp;', '&').replace('&nbsp;', ' ')
    text = re.sub(r'<[^>]+>', ' ', raw)
    text = re.sub(r'\s+', ' ', text).strip()

    ref_match = re.search(
        r'\b(Matthew|Mark|Luke|John|Acts|Romans|[12]\s*Corinthians|Galatians|Ephesians|'
        r'Philippians|Colossians|[12]\s*Thessalonians|[12]\s*Timothy|Titus|Hebrews|'
        r'James|[12]\s*Peter|[12]\s*John|Revelation|Genesis|Exodus|Psalms?|Isaiah|'
        r'Jeremiah|Ezekiel|Daniel|Hosea|Joel|Amos|Micah|Zechariah|Malachi)\s+\d+:\d+[\d\-,]*',
        text
    )
    reference = ref_match.group(0) if ref_match else "Daily Gospel"
    return reference, text[:2000]


# ── 2. Generate reflection via Ollama ─────────────────────────────────────────
def generate_reflection(reference, gospel_text):
    prompt = f"""Today's Catholic gospel is {reference}.

Full reading:
{gospel_text}

Write a message for Jair with exactly this structure:
1. A warm morning greeting (1 sentence), starting with "🙏 Bom dia, Jair!"
2. A brief summary of the gospel (2-3 sentences)
3. A personal reflection (2-3 sentences) that helps Jair feel strengthened and ready for the day

Then append on a new line: "📖 Source: {reference}"

Write ONLY the message. No extra commentary, no markdown, no headers."""

    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 400}
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "").strip()
    except Exception as e:
        return f"(Ollama error: {e})\n\n🙏 Bom dia, Jair!\n\n📖 Source: {reference}"


# ── 3. Send to Telegram ───────────────────────────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT,
        "text":    message,
        "parse_mode": ""
    }).encode()
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                print("✅ Message sent to Telegram.")
            else:
                print(f"❌ Telegram error: {result}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        sys.exit(1)


# ── 4. Generate TTS voice message ─────────────────────────────────────────────
SHERPA_RUNTIME = os.environ.get(
    "SHERPA_ONNX_RUNTIME_DIR",
    "/home/jjsantanna/.openclaw/tools/sherpa-onnx-tts/runtime"
)
SHERPA_MODEL = os.environ.get(
    "SHERPA_ONNX_MODEL_DIR",
    "/home/jjsantanna/.openclaw/tools/sherpa-onnx-tts/models/vits-piper-en_US-lessac-high"
)

def build_tts_text(message):
    """Strip emoji/URLs and fix Jair's name pronunciation for TTS."""
    import re
    # Remove URLs
    text = re.sub(r'https?://\S+', '', message)
    # Remove emoji (basic unicode ranges)
    text = re.sub(r'[\U00010000-\U0010ffff\U0001F300-\U0001F9FF\u2600-\u27BF]', '', text)
    # Replace "Jair" with phonetic spelling
    text = re.sub(r'\bJair\b', 'Zhah-eer', text)
    # Clean up extra whitespace/newlines
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_tts(message, output_path="/tmp/gospel-tts.wav"):
    """Generate TTS audio using sherpa-onnx offline TTS."""
    import subprocess
    tts_bin = os.path.join(SHERPA_RUNTIME, "bin", "sherpa-onnx-offline-tts")
    model_file = os.path.join(SHERPA_MODEL, "en_US-lessac-high.onnx")
    tokens_file = os.path.join(SHERPA_MODEL, "tokens.txt")
    data_dir = os.path.join(SHERPA_MODEL, "espeak-ng-data")

    if not os.path.exists(tts_bin):
        print(f"⚠️  sherpa-onnx-offline-tts not found at {tts_bin}, skipping TTS.")
        return None

    tts_text = build_tts_text(message)
    print(f"🔊 Generating TTS audio ({len(tts_text)} chars)...")

    result = subprocess.run(
        [
            tts_bin,
            f"--vits-model={model_file}",
            f"--vits-tokens={tokens_file}",
            f"--vits-data-dir={data_dir}",
            "--vits-length-scale=1.4",
            f"--output-filename={output_path}",
            tts_text,
        ],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0 and os.path.exists(output_path):
        print(f"   → Saved to {output_path}")
        return output_path
    else:
        print(f"❌ TTS failed: {result.stderr[-300:]}")
        return None

def send_telegram_voice(audio_path, caption=""):
    """Send a voice message via Telegram bot API."""
    import mimetypes
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVoice"
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    filename = os.path.basename(audio_path)
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{TELEGRAM_CHAT}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n'
        f"{caption}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="voice"; filename="{filename}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + audio_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                print("✅ Voice message sent to Telegram.")
            else:
                print(f"❌ Telegram voice error: {result}")
    except Exception as e:
        print(f"❌ Failed to send voice message: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📖 Fetching gospel from Universalis...")
    reference, gospel_text = fetch_gospel()
    if reference is None:
        print(f"❌ {gospel_text}")
        sys.exit(1)
    print(f"   → {reference}")

    from datetime import datetime
    today_url = f"https://universalis.com/{datetime.now().strftime('%Y-%m-%d')}/mass.htm"

    print(f"🤖 Generating reflection with {OLLAMA_MODEL}...")
    message = generate_reflection(reference, gospel_text)
    print(f"   → {len(message)} chars")

    # Append the link to the source line
    message = message.replace(
        f"📖 Source: {reference}",
        f"📖 Source: {reference}\n{today_url}"
    )

    print("📲 Sending to Telegram...")
    send_telegram(message)

    # Generate and send TTS voice message
    audio_path = generate_tts(message, output_path="/tmp/gospel-tts.wav")
    if audio_path:
        print("📲 Sending voice message to Telegram...")
        send_telegram_voice(audio_path, caption=f"Today's Gospel - {reference}")
