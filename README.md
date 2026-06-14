<div align="center">
  <h1>🤖 CodeUnfold</h1>
  <p><strong>The AI LeetCode Tutor That Actually Teaches</strong></p>
  
  <p>
    <a href="https://streamlit.io/"><img src="https://img.shields.io/badge/built_with-Streamlit-ff4b4b?style=for-the-badge&logo=streamlit&logoColor=white" alt="Built with Streamlit" /></a>
    <a href="https://groq.com/"><img src="https://img.shields.io/badge/Powered%20by-Groq-f59e0b?style=for-the-badge" alt="Powered by Groq" /></a>
    <img src="https://img.shields.io/badge/cost-100%25_free-22c55e?style=for-the-badge" alt="Free" />
    <img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="License" />
  </p>

  <p><em>Paste any LeetCode problem. Get a step-by-step lesson that teaches you how to solve it — not just the answer.</em></p>
</div>

---

## 🌟 Why CodeUnfold?

Most AI tools just spit out the final code. You copy it, paste it, pass the test, and learn absolutely nothing. **CodeUnfold is different.** It forces you to learn.

- 🧠 **Concept-First Explanations:** Every technical term gets a real-world analogy. A hash map is explained *"like a phone book where you search by name instead of flipping pages."*
- 💡 **Actionable Hints:** Stuck? Click 'Get Hints' to get the exact Data Structure, algorithm name, and the first 2 steps—without spoiling the final solution.
- ⚡ **Groq-Powered Speed:** Built on Groq (Llama 3.3 70B) for lightning-fast 2–4 second responses. Google Gemini 2.5 Flash steps in automatically as a fallback.
- 🛠️ **The Fix Loop:** Paste a LeetCode error output. The AI sees the exact failure, diagnoses the issue, and fixes the code dynamically.
- 💸 **100% Free & Open Source:** Runs entirely on free-tier APIs. No credit cards, no subscriptions, no paywalls.

---

## ✨ Features at a Glance

| Feature | Description |
| :--- | :--- |
| **💡 Multi-Tab Hints** | Get unstuck with precise nudges (Intuition, Walkthrough, Pseudocode) instead of the full code. |
| **🔍 Multi-Tab Solutions** | Full step-by-step lessons broken down into Overview, Logic, Code, and Takeaway tabs. |
| **🔧 Code Diff Fix Loop** | Paste your failing LeetCode console output; the AI automatically fixes the code and shows a red/green diff of exactly what changed. |
| **🧠 Fast Session Memory** | Instantly save 1-click takeaways to your session memory so the AI avoids repeating past mistakes. |
| **🛡️ Rate Limited** | Built-in smart rate limiting and API fallback logic to protect public deployments from abuse. |

---

## 🚀 Quick Start (Under 1 Minute)

### 1. Get Your Free API Keys
You only need one to start, but both are recommended for failover:
- **[Groq Console](https://console.groq.com)** — Fast, free, no credit card required. *(Primary)*
- **[Google AI Studio](https://aistudio.google.com)** — Generous free tier. *(Fallback)*

### 2. Clone & Setup
```bash
git clone https://github.com/mzaman001/CodeUnfold.git
cd CodeUnfold

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
```

### 3. Add Keys & Run
Edit your `.env` file and paste your API keys:
```env
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
```

Launch the app:
```bash
python -m streamlit run main.py
```
Open `http://localhost:8501` and paste your first LeetCode problem!

---

## 🏗️ Architecture & Speed

Built for lightning-fast responses and security, even on public deployments:

- **Strict UI Tab Parsing:** AI responses are strictly forced into XML-like tags, allowing the Streamlit frontend to cleanly parse walls of text into beautiful UI tabs.
- **Prompt Injection Defense:** User inputs are sanitized and isolated inside strict `<user_problem>` XML boundaries.
- **Lightning Fast In-Memory State:** Instead of clunky SQLite databases, session memory is handled purely in blazing-fast Streamlit RAM.
- **Smart Rate Limiting:** Implements both per-minute sliding window limits and per-session hard caps to prevent abuse of shared API keys.
- **Dual-Model Routing:** Automatically routes to Groq for speed, and gracefully falls back to Gemini if Groq is rate-limited.

---

## 🤝 Contributing

Contributions are always welcome! Whether it's adding new language sandboxes, improving the prompt engineering, or enhancing the UI.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

<div align="center">
  <p>If CodeUnfold helped you ace an interview, consider giving it a ⭐ on GitHub!</p>
</div>
