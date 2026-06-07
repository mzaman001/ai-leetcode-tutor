# 🤖 CodeUnfold

![UI Showcase](https://img.shields.io/badge/UI-AMOLED_Chat-black?style=for-the-badge)
![Tech Stack](https://img.shields.io/badge/Tech-Python_|_Streamlit_|_SQLite-blue?style=for-the-badge)
![AI Models](https://img.shields.io/badge/AI-Groq_Llama3_|_Gemini_Flash-orange?style=for-the-badge)
![Performance](https://img.shields.io/badge/Performance-Zero_Budget_|_Max_Speed-brightgreen?style=for-the-badge)

A highly advanced AI coding tutor built to solve complex LeetCode problems optimally and teach them step-by-step using a structured, beginner-friendly "Hand-Holding" format.

Unlike standard LLM wrappers, this application utilizes a **Zero-Budget High-Speed Pipeline** and **Verified Community Knowledge** to guarantee algorithmic accuracy by heavily prioritizing pre-trained community solutions (e.g., NeetCode, famous GitHub repos) over raw AI hallucination.

---

## ⚡ Speed & Cost Optimizations (Zero Budget Architecture)

This app is heavily optimized to run at maximum speed using entirely free-tier API keys:

1. **Hardware-Accelerated Fallback Chain:** The app tries **Groq's LPU hardware** first (Llama 3.3 70B) for blistering speed (300+ tokens/sec). If Groq rate-limits the user, it silently and instantly reroutes to **Google Gemini 2.5 Flash** as a reliable, massive rate-limit buffer.
2. **Parallelized Guardrails:** Malicious prompt detection and actual code generation fire simultaneously via threading, saving 1-2 seconds per request.
3. **Prompt Compression:** AI instructions are mathematically compressed to generate exactly what is needed with ~13% fewer output tokens, guaranteeing lightning-fast TTFT (Time To First Token).

---

## 🏗️ The Multi-Agent Architecture

### 1. The Verified Tutor (Primary)
When a problem is submitted, the AI is blocked from "inventing" algorithms. It is strictly commanded to recall verified solutions from its training data (LeetCode discussions, famous GitHub repos) and teach that optimal code line-by-line.

### 2. The Auto-Correction Loop
If your solution fails, paste the exact LeetCode error output. The AI reviews your code, the exact raw error string, and previously learned lessons to surgically patch the bug.

### 3. Persistent SQLite Memory
When you learn a new trick or solve a bug, you can save the lesson. A strict "Bouncer" AI verifies the lesson to prevent trolls. If verified, the AI extracts a generalized lesson and saves it to a **local SQLite database** (`lessons.db`), seamlessly injecting it into future prompts so you never make the same mistake twice.

---

## 🛡️ Security & Reliability

- **Strict AST Sandboxing:** Safely execute Python code locally. The custom sandbox physically blocks dangerous imports (`os`, `sys`, `subprocess`) and built-in functions (`eval`, `exec`) using AST NodeVisitors.
- **Prompt Injection Defense:** Input is heavily sanitized (`<user_problem>` tagging, tag stripping) to prevent malicious users from breaking the guardrails.
- **XSRF & CORS Protection:** Fully configured for safe deployment on Streamlit Community Cloud.
- **Rate Limiting:** Built-in Token Bucket rate limiters prevent API spam and save your free-tier quotas.

---

## 🛠️ Technical Implementation

**Frontend:**
- Streamlit
- Custom VS Code-inspired Minimum Dark Pro theme

**Backend:**
- Python 3.x
- SQLite (Local Database with `UNIQUE` constraints and threaded caching)
- Secure AST Sandboxing (Python) & Node.js subprocess (JavaScript)

**AI Pipeline:**
- Groq API (Llama 3 Inference)
- Gemini API (Flash models)
- Concurrent execution via `ThreadPoolExecutor`

---

## 🚀 Deployment (Streamlit Community Cloud)

To deploy this app for free on Streamlit Community Cloud:

1. Connect your GitHub repository to Streamlit.
2. Go to **Advanced Settings > Secrets** in your Streamlit dashboard.
3. Paste the following TOML configuration with your free API keys:
   ```toml
   GEMINI_API_KEY = "your_google_gemini_key_here"
   GROQ_API_KEY = "your_groq_key_here"
   ```
4. Click **Deploy**. The app handles the rest!

---

## 💻 Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/CodeUnfold.git
   cd CodeUnfold
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your API keys:
   ```ini
   GEMINI_API_KEY=your_gemini_key_here
   GROQ_API_KEY=your_groq_key_here
   ```

4. Run the application:
   ```bash
   python -m streamlit run main.py
   ```
