<div align="center">
  <h1>
    🙏 Daily Gospel → Telegram [OpenClaw]
  </h1>
  <img src="https://img.shields.io/badge/DoneBy-OpenClaw-red">
  <img src="https://img.shields.io/badge/Python-Script-blue">
  <img src="https://img.shields.io/badge/Ollama-gemma3:4b-green">
  
  A daily gospel message delivered to Telegram every morning at 7:00 AM (Amsterdam time), powered by a local Ollama model — **zero API cost**.
</div>

## How It Works

1. A cron job fires at **7:00 AM Europe/Amsterdam** via [OpenClaw](https://openclaw.ai)
2. `fetch_gospel.py` scrapes today's Catholic daily gospel from [Universalis](https://universalis.com)
3. The gospel text is passed to **gemma3:4b** running locally via Ollama
4. The model writes a warm, personal reflection message
5. The message is delivered to Telegram with the gospel source appended

## Message Format

```
🙏 Bom dia, Jair!

[Warm greeting]

[Brief gospel summary — 2-3 sentences]

[Personal reflection to start the day stronger — 2-3 sentences]

📖 Source: Matthew 5:17-19
```

## Files

- `fetch_gospel.py` — Scrapes today's gospel from Universalis and extracts the reference
- `README.md` — This file

## Setup

### Requirements

- [OpenClaw](https://openclaw.ai) gateway running
- [Ollama](https://ollama.ai) with `gemma3:4b` installed (`ollama pull gemma3:4b`)
- Python 3

### Ollama Provider (openclaw.json)

```json
"models": {
  "mode": "merge",
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "apiKey": "ollama",
      "api": "ollama",
      "models": [
        {
          "id": "gemma3:4b",
          "name": "Gemma 3 4B (local)",
          "reasoning": false,
          "input": ["text"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
          "contextWindow": 32768,
          "maxTokens": 4096
        }
      ]
    }
  }
}
```

### Cron Job

```bash
openclaw cron add \
  --name "Daily Gospel" \
  --cron "0 7 * * *" \
  --tz "Europe/Amsterdam" \
  --session isolated \
  --model "ollama/gemma3:4b" \
  --light-context \
  --message 'Run: python3 /path/to/fetch_gospel.py

Parse the output: the REFERENCE line gives the gospel source, the TEXT line gives the full reading.

Write a message for Jair with exactly this structure:
1. A warm morning greeting (1 sentence), starting with "🙏 Bom dia, Jair!"
2. A brief summary of the gospel (2-3 sentences)
3. A personal reflection (2-3 sentences) that helps Jair feel strengthened and ready for the day

Then append on a new line: "📖 Source: [REFERENCE]" using the exact reference from the script output.

Write ONLY the message, no extra commentary.' \
  --announce \
  --channel telegram \
  --to "YOUR_TELEGRAM_ID" \
  --exact
```

## Model Hierarchy

| Role | Model | Notes |
|------|-------|-------|
| Main agent | `anthropic/claude-sonnet-4-6` | Tool-heavy sessions |
| Fallback | `anthropic/claude-haiku-4-5` | Rate limit fallback |
| Daily Gospel | `ollama/gemma3:4b` | Local, free, zero cost |
| Deep work | `anthropic/claude-opus-4-6` | Manual `/model` switch only |

## Why gemma3:4b?

- Best quality among available local models
- Only ~3.3 GB — fits comfortably in 16 GB RAM
- No GPU required (CPU inference)
- Free — no API costs
