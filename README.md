# 🤖 CodeUnfold

![UI Showcase](https://img.shields.io/badge/UI-AMOLED_Chat-black?style=for-the-badge)
![Tech Stack](https://img.shields.io/badge/Tech-Python_|_Streamlit-blue?style=for-the-badge)
![AI Models](https://img.shields.io/badge/AI-Groq_|_Gemini-orange?style=for-the-badge)

A highly advanced AI coding tutor built to solve complex LeetCode problems optimally and teach them step-by-step using a literal "Hand-Holding" pair-programmer format.

Unlike standard LLM wrappers, this application utilizes a **Unified Agentic Tutor Pipeline** designed to guarantee algorithmic accuracy by having the AI mentally verify code *before* it begins teaching it.

---

## 🏗️ The Multi-Agent Architecture

This project solves the famous AI "Blind Leading the Blind" problem through robust guardrails and strict pedagogical prompting.

### 1. The Agentic Tutor (Primary)
When a problem is submitted, the AI (Gemini or Groq) is forced into a strict pedagogical structure. It must first write the optimal code and then immediately break it down line-by-line. This unified approach prevents the AI from trying to teach incorrect code.

### 2. The Auto-Correction Loop
If the solution fails in your testing environment, you can paste the error output. The AI reviews the **exact raw code** that failed along with your error string, surgically patching the bug while leveraging previous debugging context to avoid recurring errors.

### 3. The "Bouncer" AI & Session Memory
If you learn a new trick from a failed attempt, you can submit your terminal output proof. A strict "Bouncer" AI (Llama 3.1 8B via Groq) verifies the execution proof to prevent trolls. If verified, the AI extracts a generalized lesson and saves it to your **isolated session memory**, injecting it into future prompts to prevent repeating mistakes.

---

## 📊 Core Architecture Goals

- **Perfect Pedagogy:** Forces the LLM to define every technical term from scratch and explain code in 1-3 line chunks.
- **Isolated Memory:** Uses pure `st.session_state` for memory to guarantee zero cross-user data leakage and instant performance without database overhead.
- **Auto-Downgrade Resilience:** A massive 4-stage fallback chain automatically routes around rate limits and 413 token limits (User Key → Gemini models → Groq 70B → Groq 8B).
- **Token Efficiency:** Raw code and markdown lessons are stored separately in state to prevent token explosion during the error-correction loops.

---

## 🛠️ Technical Implementation

**Frontend:**
- Streamlit
- Custom VS Code-inspired Minimum Dark Pro theme

**Backend:**
- Python
- Groq API (Llama 3 Inference)
- Gemini API (Flash models)

**AI Pipeline:**
- Unified Tutor Agent (Logic generation + Educational breakdown)
- Verification Agent (Bouncer logic)

---

## ✨ Features

- **True IDE Aesthetics:** Cohesive, deep slate VS Code AMOLED theme with vibrant Fira Code typography and amber accents.
- **Chat-Not-Chat Layout:** Cleanly separates the problem description from the massive, hand-holding tutor explanations.
- **BYOK (Bring Your Own Key) Failsafe:** A sleek sidebar toggle allows power users to bypass the free-tier rate limits by injecting their own API keys dynamically without crashing the fallback chain.
- **Strict Guardrails:** An LLM-powered classifier blocks non-coding inputs to save tokens.

---

## 🚀 Future Roadmap

- **LeetCode URL Auto-Fetch:** Headless scraping using Playwright to instantly extract problem descriptions and constraints from LeetCode URLs.
- **Spaced Repetition Dashboard:** A custom UI that resurfaces previously failed problems using a spaced-repetition algorithm to guarantee interview readiness.

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
   *(Note: The app works entirely offline from databases. No Supabase configuration required!)*

4. Run the application:
   ```bash
   streamlit run app.py
   ```
