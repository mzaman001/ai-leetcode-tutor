# 🤖 Universal AI Coding Tutor

![UI Showcase](https://img.shields.io/badge/UI-AMOLED_Chat-black?style=for-the-badge)
![Tech Stack](https://img.shields.io/badge/Tech-Python_|_Streamlit_|_Supabase-blue?style=for-the-badge)
![AI Models](https://img.shields.io/badge/AI-Groq_70B_|_Gemini_Flash-orange?style=for-the-badge)

A highly advanced, multi-agent AI coding tutor built to solve complex LeetCode problems optimally and teach them step-by-step using a literal "Hand-Holding" pair-programmer format.

Unlike standard LLM wrappers, this application utilizes a custom **Agentic Generator-Tutor Pipeline** combined with a **Long-Term Database Memory (RAG)** system to ensure 99th-percentile algorithmic accuracy and a flawless, hallucination-free teaching persona.

---

## 🏗️ The Multi-Agent Architecture

This project solves the famous AI "Blind Leading the Blind" problem by separating the algorithmic logic generation from the user-facing persona.

### 1. The Agentic Generator (Groq Llama 3 70B)
When a problem is submitted, it is first routed to Groq's Llama 3 70B model via a high-speed inference API. The model is given a strict **Hardcore Runtime Directive**: it must identify the mathematically optimal approach (e.g., O(1) space, O(N) time) and output *pure, flawless Python code* without any explanations. This guarantees elite competitive-programming level accuracy.

### 2. The Agentic Tutor (Gemini 2.5 Flash)
Once the perfect code is generated, it is passed internally to Gemini 2.5 Flash. Gemini is strictly isolated from algorithmic generation and is instructed purely to act as the world's most patient tutor. It executes a **Line-by-Line Code Breakdown**, explaining the exact mechanics of the syntax, variables, and logic behind the provided solution.

### 3. The "Bouncer" AI & Long-Term Memory (Supabase RAG)
If a user learns a new trick from a failed attempt, they can submit their terminal output proof. A strict "Bouncer" AI (Llama 3.1 8B) verifies the execution proof to prevent trolls. If verified, the AI extracts a generalized lesson and saves it to a Supabase PostgreSQL database. All future AI prompts are injected with these past lessons, allowing the app to literally get smarter over time.

---

## ✨ Features

- **True IDE Aesthetics:** A native Streamlit `config.toml` implementation forces a cohesive, deep slate VS Code AMOLED theme with vibrant Fira Code typography.
- **Chat-Not-Chat Layout:** Utilizes Streamlit's native Chat Timeline UI to cleanly separate the problem description from the massive, hand-holding tutor explanations.
- **Auto-Correction Loop:** An anchored chat input allows users to paste specific terminal errors. The AI reviews its own attempt history and surgically patches the bug without ever repeating the same mistake.
- **BYOK (Bring Your Own Key) Failsafe:** A sleek sidebar toggle allows power users to bypass the free-tier rate limits by injecting their own API keys dynamically.

---

## 🚀 Future Roadmap

- **LeetCode URL Auto-Fetch:** Headless scraping using Playwright to instantly extract problem descriptions and constraints from LeetCode URLs.
- **Full User Authentication:** Supabase Auth integration to track individual user progress, difficulty ratings, and success rates.
- **Spaced Repetition Algorithm:** A custom dashboard that resurfaces previously failed problems using a spaced-repetition algorithm to guarantee interview readiness.

---

## 💻 Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-leetcode-tutor.git
   cd ai-leetcode-tutor
   ```

2. Install dependencies:
   ```bash
   pip install streamlit google-genai groq supabase python-dotenv
   ```

3. Create a `.env` file in the root directory and add your API keys:
   ```ini
   GEMINI_API_KEY=your_gemini_key_here
   GROQ_API_KEY=your_groq_key_here
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_key_here
   ```

4. Run the application:
   ```bash
   streamlit run app.py
   ```
