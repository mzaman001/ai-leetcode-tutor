# CodeUnfold — AI LeetCode Tutor That Actually Teaches

> Paste any LeetCode problem. Get a step-by-step lesson that teaches you how to solve it — not just the answer.

![CodeUnfold Demo](https://img.shields.io/badge/built_with-Streamlit-ff4b4b?style=flat-square) ![Free](https://img.shields.io/badge/cost-100%25_free-22c55e?style=flat-square) ![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)

---

## What It Does

| Feature | Description |
|---|---|
| **💡 Get Hints** | Tells you the exact Data Structure, algorithm, first steps, and target complexity — without spoiling the solution |
| **🔍 Reveal Solution** | Full step-by-step lesson with real-world analogies. Every term explained inline. No Googling needed. |
| **▶ Run Code** | Execute the generated solution locally to verify it works before submitting |
| **🔧 Fix Loop** | Paste a LeetCode error — the AI diagnoses and fixes it automatically |
| **🧠 Session Memory** | Save proven solutions. The AI remembers your past mistakes and avoids them in future explanations |

---

## Quick Start (30 seconds)

**1. Get a free API key**
- [Groq](https://console.groq.com) — Fast, free, no credit card (recommended)
- [Google AI Studio](https://aistudio.google.com) — Generous free tier (backup)

**2. Clone and run**
```bash
git clone https://github.com/mzaman001/CodeUnfold.git
cd CodeUnfold
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API key
python -m streamlit run main.py
```

**3. Open** `http://localhost:8501` and paste any LeetCode problem.

---

## How It's Different

Most AI tools just give you the answer. CodeUnfold teaches:

- **Concept-first explanations** — Every term gets an analogy. A hash map is explained *"like a phone book where you search by name instead of flipping pages."*
- **Hints that actually help** — Get the right Data Structure, the algorithm name, the first 2 steps, and the target complexity. Concrete, not vague.
- **Groq-powered speed** — 2–4 second responses via Llama 3.3 70B, with Gemini Flash as automatic backup
- **Fix loop** — Paste any LeetCode error output. The AI sees the exact failure and fixes the code
- **100% free** — Runs entirely on free-tier APIs. No credit card, no subscription

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Primary AI | Groq (Llama 3.3 70B) |
| Backup AI | Google Gemini 2.5 Flash |
| Code Execution | Python subprocess + AST sandbox |
| Memory | SQLite (local) |
| Security | Input sanitization + guardrail classifier + rate limiting |

---

## Self-Hosting

Add your API keys to `.env`:
```
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

Then run:
```bash
python -m streamlit run main.py
```

---

## Architecture Notes

- **Guardrail classifier**: Every input is checked by a fast Groq Llama model before the main AI call. Non-coding inputs are rejected without burning quota.
- **AST sandbox**: Python code is scanned for dangerous imports (`os`, `subprocess`, `socket`, etc.) before execution.
- **Rate limiting**: Per-session call caps + per-minute sliding window limiters protect shared API quota.
- **Prompt injection defense**: User input is sanitized and isolated inside `<user_problem>` XML tags with injection phrase detection.

---

## Contributing

PRs welcome. Open an issue first for major changes.

---

*Built by [Muhammad Zaman](https://github.com/mzaman001)*
