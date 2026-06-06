import streamlit as st
from google import genai
from google.genai import types
from groq import Groq
import os
from dotenv import load_dotenv
import re
import subprocess
import tempfile
import sys

load_dotenv()

st.set_page_config(page_title="CodeUnfold", page_icon="🤖", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Inter:wght@400;500;600&display=swap');

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }

    ::selection { background: rgba(245, 158, 11, 0.3); color: #f8fafc; }

    .stApp { background-color: #0a0a0f !important; }
    section.main { overflow-anchor: none !important; }
    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #f59e0b, #f97316);
        z-index: 999;
    }

    h1, h2, h3, p, li, label {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    .stTextArea textarea {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border: 1px solid #334155 !important;
        color: #fef3c7 !important;
        font-family: 'Fira Code', monospace !important;
        border-radius: 8px !important;
        transition: border-color 0.2s ease !important;
        box-shadow: none !important;
    }
    .stTextArea textarea:focus {
        border-color: #f59e0b !important;
        box-shadow: none !important;
    }

    span[class*="material-symbols"], i[class*="material-symbols"], .material-icons {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }

    code {
        font-family: 'Fira Code', monospace !important;
        color: #f59e0b !important;
    }
    pre {
        background: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px !important;
        padding: 16px !important;
        box-shadow: none !important;
    }
    pre code { color: #f8fafc !important; }

    [data-testid="stChatMessage"] {
        background: rgba(15, 23, 42, 0.5) !important;
        border: none !important;
        border-left: 3px solid #f59e0b !important;
        border-radius: 0 12px 12px 0 !important;
        padding: 20px 24px !important;
        margin-bottom: 16px !important;
        box-shadow: none !important;
    }
    [data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        border-left-color: #64748b !important;
    }

    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        text-transform: none !important;
        letter-spacing: normal !important;
        border-radius: 999px !important;
        padding: 8px 24px !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(245, 158, 11, 0.08) !important;
        border: 1px solid rgba(245, 158, 11, 0.2) !important;
        color: #fcd34d !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(245, 158, 11, 0.15) !important;
        border-color: #f59e0b !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="primary"] {
        background: #f59e0b !important;
        border: none !important;
        color: #000 !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        opacity: 0.9 !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #0d0d14 !important;
        border-right: 1px solid #1a1a24 !important;
    }
</style>
""", unsafe_allow_html=True)


# ---------- AI Clients (cached — created only once per server session) ----------
@st.cache_resource
def _init_clients():
    api_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None, None
    gemini = genai.Client(api_key=api_key)
    groq = Groq(api_key=groq_key) if groq_key else None
    return gemini, groq

_default_gemini, _groq_client = _init_clients()

if not _default_gemini:
    st.warning("⚠️ `GEMINI_API_KEY` environment variable is not set.")
    st.stop()

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
GROQ_MAIN_MODEL = "llama-3.3-70b-versatile"
GROQ_FAST_MODEL = "llama-3.1-8b-instant"
BOUNCER_MODEL = GROQ_FAST_MODEL


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### ⚙️ API Settings")
    st.markdown("Add your own key to bypass free-tier rate limits.")
    user_gemini_key = st.text_input("Your Gemini API Key (Optional)", type="password")
    if user_gemini_key:
        st.success("Using your personal Gemini key!")
    st.divider()

    st.markdown("### 🧠 Session Memory")
    _lessons = st.session_state.get("lessons", [])
    if _lessons:
        st.caption(f"{len(_lessons)} lesson(s) saved this session.")
        for _l in _lessons[-3:]:
            st.caption(f"• {_l[:70]}{'...' if len(_l) > 70 else ''}")
    else:
        st.caption("No lessons yet. Verify a correct solution to start building your memory!")


# ---------- Session State ----------
_defaults = {
    "problem_text": "",
    "current_solution": None,
    "current_hints": None,
    "raw_code": "",           # Raw code extracted from solution, used in fix prompts
    "show_update_alert": False,
    "lesson_saved": False,
    "last_saved_lesson_text": "",
    "lessons": [],            # In-session lesson memory (no database, no leakage)
    "attempt_errors": [],     # Only error strings, not full markdown solutions
    "execution_output": None, # Latest run result: {"stdout": str, "stderr": str, "success": bool}
}
for key, default in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------- Helpers ----------
def get_lessons_context() -> str:
    """Returns at most 5 recent lessons as a formatted string. Prevents token explosion."""
    lessons = st.session_state.get("lessons", [])
    if not lessons:
        return ""
    recent = lessons[-5:]
    return "\n\nLESSONS FROM YOUR MEMORY (avoid repeating past mistakes):\n" + "\n".join(f"- {l}" for l in recent)


def save_lesson(lesson_text: str):
    st.session_state.lessons.append(lesson_text)


def call_ai(prompt: str, user_key: str = None) -> str:
    """
    AI Engine: User Key → Gemini chain → Groq chain (70B → 8B).
    - User key failure gracefully falls through to the default chain.
    - Groq auto-retries with a smaller model on token limit errors.
    """
    # 1. User-provided key (graceful fallback on failure — never hard crashes)
    if user_key:
        try:
            temp_client = genai.Client(api_key=user_key)
            response = temp_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            st.sidebar.caption("🤖 Answered by: `gemini-2.5-flash` (your key)")
            parts = [p.text for c in response.candidates for p in c.content.parts if p.text]
            return "\n".join(parts) if parts else response.text
        except Exception as e:
            st.sidebar.warning(f"⚠️ Your personal key failed (`{str(e)[:60]}`). Falling back to shared models...")
            # Intentional fall-through to default chain

    # 2. Default Gemini chain
    last_error = None
    for model_id in GEMINI_MODELS:
        try:
            response = _default_gemini.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            parts = [p.text for c in response.candidates for p in c.content.parts if p.text]
            st.sidebar.caption(f"🤖 Answered by: `{model_id}`")
            return "\n".join(parts) if parts else response.text
        except Exception as e:
            last_error = e
            err = str(e)
            if "404" in err or "NOT_FOUND" in err:
                st.sidebar.caption(f"⚠️ `{model_id}` unavailable, skipping...")
            elif "429" in err or "RESOURCE_EXHAUSTED" in err:
                st.sidebar.caption(f"⚡ `{model_id}` rate-limited, trying next...")
            else:
                st.sidebar.caption(f"❌ `{model_id}` error, trying next...")
            continue

    # 3. Groq chain — 70B first, auto-downgrade to 8B on token limit errors
    if _groq_client:
        st.sidebar.caption("🔄 Gemini exhausted. Switching to Groq backup...")
        sys_msg = "You are an expert Python developer and CS tutor. Be thorough, accurate, and beginner-friendly."
        groq_attempts = [
            (GROQ_MAIN_MODEL, prompt),
            (GROQ_FAST_MODEL, prompt[:15000]),  # Safely truncated for smaller model
        ]
        for groq_model, groq_prompt in groq_attempts:
            try:
                completion = _groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": groq_prompt},
                    ],
                    model=groq_model,
                    temperature=0.2,
                )
                st.sidebar.caption(f"🤖 Answered by: `{groq_model}` (Groq)")
                return completion.choices[0].message.content
            except Exception as e:
                last_error = e
                err = str(e)
                if "413" in err or "too large" in err.lower() or "429" in err:
                    st.sidebar.caption(f"⚡ `{groq_model}` limit hit, trying smaller model...")
                    continue
                break  # Non-retriable error

    # 4. Total failure — honest message about what actually failed
    groq_note = (
        "Groq backup is unavailable (no API key configured)."
        if not _groq_client
        else "Groq backup is also rate-limited."
    )
    raise Exception(
        f"🛑 All AI providers temporarily unavailable. Gemini is rate-limited and {groq_note}\n\n"
        f"Paste your own Gemini API key into the sidebar to continue instantly.\n"
        f"(Debug: {str(last_error)[:120]})"
    )


def check_guardrail(text: str, user_key: str = None) -> bool:
    """Checks if the input is actually a coding-related problem."""
    if len(text.strip()) < 10:
        return False
    prompt = (
        "You are a strict binary classifier. Reply with ONLY the word 'YES' or 'NO' — nothing else.\n\n"
        "Is the following input a coding problem, algorithm question, programming assignment, "
        "code snippet, or technical debugging task?\n\n"
        "Answer NO for: general chat, recipes, essays, math riddles, or anything unrelated to software/programming.\n\n"
        f"Input: {text[:600]}"
    )
    try:
        if _groq_client:
            r = _groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=BOUNCER_MODEL,
                temperature=0.0,
                max_tokens=5,
            )
            return "YES" in r.choices[0].message.content.upper()
        else:
            return "YES" in call_ai(prompt, user_key).upper()
    except Exception:
        return True  # Fail open if guardrail itself crashes


def execute_code(code: str, timeout: int = 10) -> dict:
    """
    Runs a Python code string in a subprocess with a timeout.
    Returns {"stdout": str, "stderr": str, "success": bool}.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"⏱️ Execution timed out after {timeout}s. Your code may have an infinite loop.",
            "success": False,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "success": False}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _trigger_fix_loop(prob_text: str, errors: list, user_key: str = None):
    """
    Shared helper: builds the fix prompt, calls the AI, updates session state.
    Used by both the manual error expander and the Run Code auto-send button.
    """
    error_history = "\n".join(f"Error #{i + 1}:\n{e}" for i, e in enumerate(errors))
    code_to_fix = st.session_state.raw_code or "(code unavailable — infer from the problem)"
    fix_prompt = f"""You are an expert Python debugger and LeetCode Grandmaster.

PROBLEM:
{prob_text}

CODE THAT FAILED:
```python
{code_to_fix}
```

ALL ERRORS SO FAR (do NOT repeat these mistakes):
{error_history}

INSTRUCTIONS:
1. Identify the root cause of each error above.
2. Do NOT reuse any previously failed approach.
3. Write a fully correct, optimal, Pythonic solution that is compatible with Python 3.8+.
4. Mentally trace through at least 2 test cases (including an edge case) before responding.

RESPONSE FORMAT:

## 🔍 What Went Wrong
Clear explanation of the bug(s) in plain language.

## ✅ Corrected Solution
The complete, working Python code in a ```python block.

## 📖 What Changed and Why
Explain the fix step by step for a beginner.

## ✔️ Verification
Trace through one example to prove the fix works.

## 💡 Proposed Lesson
A 1-sentence generalized takeaway. Label it as unverified.
{get_lessons_context()}"""
    with st.spinner("Analyzing error and generating fix..."):
        try:
            new_text = call_ai(fix_prompt, user_key)
            new_code_match = re.search(r"```python\n(.*?)```", new_text, re.DOTALL)
            if new_code_match:
                st.session_state.raw_code = new_code_match.group(1).strip()
            st.session_state.current_solution = new_text
            st.session_state.show_update_alert = True
            st.session_state.execution_output = None  # Clear stale run result
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred: {e}")


# ---------- UI ----------
def _sync_problem():
    """Sync text area → session state. Clears stale results when the problem changes."""
    new_text = st.session_state._problem_widget
    if new_text != st.session_state.problem_text:
        st.session_state.problem_text = new_text
        st.session_state.current_solution = None
        st.session_state.current_hints = None
        st.session_state.raw_code = ""
        st.session_state.attempt_errors = []
        st.session_state.lesson_saved = False
        st.session_state.execution_output = None


st.title("CodeUnfold")
st.markdown(
    "Paste any coding problem below. Get **hints** to solve it yourself, "
    "or **reveal the full solution** for a complete step-by-step lesson."
)

st.text_area(
    "Paste your coding problem here:",
    height=200,
    key="_problem_widget",
    value=st.session_state.problem_text,
    on_change=_sync_problem,
    placeholder="Paste the problem description here...",
)
st.info(
    "💡 **Pro tip for best results:** Copy both the **problem description** AND the "
    "**starter code template** from LeetCode and paste both here. "
    "The starter code tells the AI the exact method signature and class structure LeetCode expects, "
    "which significantly improves first-try accuracy."
)

problem_text = st.session_state.problem_text

col1, col2 = st.columns(2)
with col1:
    hint_button = st.button("💡 Get Hints", use_container_width=True)
with col2:
    solve_button = st.button("🔍 Reveal Solution", use_container_width=True, type="primary")


# ---------- Hint Logic ----------
if hint_button and problem_text:
    with st.spinner("Checking input..."):
        if not check_guardrail(problem_text, user_gemini_key):
            st.session_state.current_solution = None
            st.session_state.current_hints = None
            st.warning("That doesn't look like a coding problem. Please paste a valid programming question.")
            st.stop()

    lessons_context = get_lessons_context()
    hint_prompt = f"""You are a LeetCode Grandmaster and patient tutor. The student wants to solve this themselves — give hints ONLY. No code whatsoever.

## 💭 1. What's This Problem Really Asking?
Restate in simpler terms. Point out the key observation without revealing the approach.

## 🧠 2. Concepts You'll Need
For each relevant data structure or technique:
- **What is it?** Simple definition with a real-world analogy
- **Why might it help here?** A hint at the connection

## 🪜 3. Step-by-Step Thinking Path (no code, no pseudo-code)
3–5 numbered hints building toward the solution. Each must be a question or thought-provoker, not an instruction.

## ⚠️ 4. Common Pitfalls
1–2 mistakes beginners often make. Warn without revealing how to avoid them.
{lessons_context}

Problem: {problem_text}

CRITICAL: Do NOT write any code or reveal the full algorithm. Hints only."""

    try:
        with st.spinner("Thinking through hints..."):
            result = call_ai(hint_prompt, user_gemini_key)
        st.session_state.current_hints = result
        st.session_state.current_solution = None
        st.rerun()
    except Exception as e:
        st.error(f"An error occurred: {e}")

elif hint_button and not problem_text:
    st.warning("Paste a problem description above to begin.")


# ---------- Solve Logic ----------
elif solve_button and problem_text:
    with st.spinner("Checking input..."):
        if not check_guardrail(problem_text, user_gemini_key):
            st.session_state.current_solution = None
            st.session_state.current_hints = None
            st.warning("That doesn't look like a coding problem. Please paste a valid programming question.")
            st.stop()

    st.session_state.attempt_errors = []
    st.session_state.lesson_saved = False
    lessons_context = get_lessons_context()

    # Single unified prompt — the AI writes the code AND teaches it in one shot.
    # This eliminates the broken 2-step pipeline where Groq wrote code and
    # Gemini was told to teach it as "perfect" without verification.
    solve_prompt = f"""You are a world-class computer science tutor and expert Python developer.

A student has given up on this problem. Your job is two things in one response:
1. Write the most optimal, clean, Pythonic Python solution
2. Teach that exact solution from scratch in beginner-friendly language

IMPORTANT: Write the code yourself first, verify it mentally against at least 2 edge cases, then teach it. Be confident the code is correct before presenting it.

Follow this EXACT structure:

## 📌 1. What Are We Solving?
Restate in one plain-English sentence. Then:
- **Input:** What are we given? (type, range, example)
- **Output:** What must we return?
- **Constraints:** What do the limits tell us? (e.g., n ≤ 10⁵ means O(n²) is too slow)

Keep this to 3–4 lines max.

## 🧱 2. The Core Concepts
For each data structure, algorithm, or technique in your solution:
- **What is it?** Simple definition + real-world analogy
- **Why here?** Why this concept fits THIS specific problem
- **Visualize it:** Help the student picture it

Order concepts so each builds on the last. Max 4–5 sentences per concept.

## 🪜 3. Building the Solution (No Code Yet)
Walk through the algorithm in plain English. Numbered steps, one idea per step. At each decision point explain WHY this way and not another. End with 2–3 line pseudo-code.

## 🐍 4. The Code
Present your complete, optimal Python solution. It MUST be syntactically correct, properly indented, and formatted in a ```python code block.

## 🔬 5. Line-by-Line Breakdown
Take 1–3 lines at a time:
```python
# the lines
```
- **What it does:** One plain-language sentence
- **Variable state:** What each variable holds after this line
- **Watch out:** Common beginner misunderstanding

Cover every meaningful line.

## ✅ 6. Trace Through an Example
Pick the simplest meaningful input. Trace step-by-step:
| Step | Code | Variable State | Why |
|---|---|---|---|

Show the full journey from input → output.

## 📊 7. Complexity
- **Time:** Why O(...)? Plain English.
- **Space:** Where does the memory come from?

## 💡 8. Key Takeaway
One sentence for similar future problems.
{lessons_context}

Problem:
{problem_text}"""

    try:
        with st.spinner("Generating your personalized lesson..."):
            result = call_ai(solve_prompt, user_gemini_key)

        # Strip any internal scratchpad thinking
        result = re.sub(r"<scratchpad>.*?</scratchpad>", "", result, flags=re.IGNORECASE | re.DOTALL)

        # Extract raw code and store separately — this is what fix prompts will use,
        # NOT the 600-line markdown lesson (which was the original bug)
        code_match = re.search(r"```python\n(.*?)```", result, re.DOTALL)
        st.session_state.raw_code = code_match.group(1).strip() if code_match else ""

        st.session_state.current_solution = result.strip()
        st.session_state.current_hints = None
        st.session_state.show_update_alert = False
        st.session_state.lesson_saved = False
        st.rerun()
    except Exception as e:
        st.error(f"An error occurred: {e}")

elif solve_button and not problem_text:
    st.warning("Paste a problem description above to begin.")


# ---------- Display Hints ----------
if st.session_state.current_hints and not st.session_state.current_solution:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**Problem:** {problem_text[:80]}{'...' if len(problem_text) > 80 else ''}")
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("### 💡 Hints & Strategy")
        st.write(st.session_state.current_hints)


# ---------- Display Solution + Fix Loop ----------
if st.session_state.current_solution:

    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**Problem:** {problem_text[:80]}{'...' if len(problem_text) > 80 else ''}")

    with st.chat_message("assistant", avatar="🤖"):
        # Delay scroll by 150ms so it fires AFTER Streamlit finishes adding all DOM elements.
        # Without the delay, the scroll fires too early and the page renders below the top.
        st.html('<script>setTimeout(function(){ window.parent.document.querySelector("section.main").scrollTo({top: 0, behavior: "smooth"}); }, 150);</script>')

        if st.session_state.show_update_alert:
            st.success("Solution updated based on your error report.")
            st.session_state.show_update_alert = False

        st.markdown("### Solution Breakdown")
        st.write(st.session_state.current_solution)

        error_count = len(st.session_state.attempt_errors)
        if error_count > 0:
            st.caption(f"🔄 Revised {error_count} time(s) based on your feedback.")

        # --- Save to Memory ---
        if st.session_state.get("lesson_saved", False):
            st.success("✅ Saved to session memory!", icon="🧠")
            if st.button("Undo (Remove from Memory)"):
                last = st.session_state.get("last_saved_lesson_text", "")
                if last in st.session_state.lessons:
                    st.session_state.lessons.remove(last)
                st.session_state.lesson_saved = False
                st.rerun()
        else:
            # Problem-specific key prevents toggle from staying "on" across different problems
            toggle_key = f"save_toggle_{abs(hash(problem_text)) % 1_000_000}"
            show_save = st.toggle("💾 Save this approach to memory", key=toggle_key)
            if show_save:
                proof_text = st.text_area(
                    "Paste your execution output (e.g., 'Accepted', 'Passed 57/57 test cases'):",
                    height=68,
                    key="proof_input",
                )
                if st.button("Verify & Save", use_container_width=True, type="primary"):
                    if not proof_text or len(proof_text.strip()) < 3:
                        st.error("Please provide actual proof of execution.")
                    elif not _groq_client:
                        st.error("Groq API key required for Bouncer AI. Add GROQ_API_KEY to your environment.")
                    else:
                        # Truncate to safely fit the 8B model's context window
                        safe_code = (st.session_state.raw_code or st.session_state.current_solution)[:3000]
                        bouncer_prompt = (
                            f"You are a strict Bouncer AI. A student claims an AI solution worked.\n"
                            f'Their proof: "{proof_text[:500]}"\n\n'
                            f"Rules:\n"
                            f"1. If the proof is a casual comment or troll (e.g., 'it worked', 'yes', '123'), output exactly: REJECT\n"
                            f"2. If the proof looks like real execution output (e.g., 'Accepted', 'Passed', 'Runtime: 42ms', 'exit code 0'), "
                            f"extract a 1-sentence generalized lesson about WHY this approach works well. Wrap it in <LESSON> tags.\n\n"
                            f"Problem: {problem_text[:800]}\n"
                            f"Solution code:\n```python\n{safe_code}\n```"
                        )
                        with st.spinner("Bouncer AI verifying..."):
                            try:
                                r = _groq_client.chat.completions.create(
                                    messages=[{"role": "user", "content": bouncer_prompt}],
                                    model=BOUNCER_MODEL,
                                    temperature=0.1,
                                )
                                reply = r.choices[0].message.content.strip()
                                if "REJECT" in reply:
                                    st.error("🛑 Bouncer Rejected: That doesn't look like real execution output. Nice try! 😉")
                                else:
                                    m = re.search(r"<LESSON>(.*?)</LESSON>", reply, re.IGNORECASE | re.DOTALL)
                                    lesson = "✅ PROVEN: " + (
                                        m.group(1).strip() if m
                                        else (reply.replace("REJECT", "").strip() or "Solution approach verified working.")
                                    )
                                    save_lesson(lesson)
                                    st.session_state.last_saved_lesson_text = lesson
                                    st.session_state.lesson_saved = True
                                    st.balloons()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Bouncer AI error: {e}")

    # --- Run Code Section ---
    if st.session_state.raw_code:
        with st.expander("▶ Run Code — Quick Sanity Check", expanded=bool(st.session_state.execution_output)):
            st.info(
                "⚠️ **This is a local sanity check only.** The AI generates a few simple test cases from the problem "
                "description. Passing here does **not** guarantee the code will pass on LeetCode, which tests "
                "hundreds of edge cases against its own environment."
            )

            if st.button("▶ Run Code", type="primary", use_container_width=True, key="run_code_btn"):
                # Ask Groq fast model to build a complete runnable script with test cases.
                # We use the fast model here to save quota — this is just scaffolding, not teaching.
                harness_prompt = (
                    f"You are a Python expert. Create a complete standalone runnable Python test script.\n\n"
                    f"REQUIREMENTS:\n"
                    f"1. Include ALL necessary imports (e.g., from typing import List, Optional, Dict, etc.)\n"
                    f"2. Include the provided solution class/function EXACTLY as written — no changes\n"
                    f"3. After the class/function, add 2–3 test cases using examples from the problem\n"
                    f"4. Print the output of each test case clearly (e.g., print(f'Test 1: {{result}}'))\n"
                    f"5. Output ONLY the raw Python code — no markdown, no explanations, no triple backticks\n\n"
                    f"Problem:\n{problem_text[:600]}\n\n"
                    f"Solution code:\n{st.session_state.raw_code}"
                )
                with st.spinner("Building test harness and running code..."):
                    try:
                        if _groq_client:
                            harness_resp = _groq_client.chat.completions.create(
                                messages=[{"role": "user", "content": harness_prompt}],
                                model=GROQ_FAST_MODEL,
                                temperature=0.1,
                            )
                            runnable_code = harness_resp.choices[0].message.content.strip()
                        else:
                            runnable_code = call_ai(harness_prompt, user_gemini_key)

                        # Strip markdown fences if the model wrapped the code anyway
                        runnable_code = re.sub(r"^```(?:python)?\n?", "", runnable_code.strip(), flags=re.MULTILINE)
                        runnable_code = re.sub(r"\n?```$", "", runnable_code.strip(), flags=re.MULTILINE)

                        result = execute_code(runnable_code)
                        st.session_state.execution_output = result
                        st.rerun()
                    except Exception as e:
                        st.session_state.execution_output = {"stdout": "", "stderr": str(e), "success": False}
                        st.rerun()

            # Display execution result
            if st.session_state.execution_output:
                out = st.session_state.execution_output
                if out["success"] and out["stdout"].strip():
                    st.success("✅ Passed local sanity check (AI-generated test cases only)")
                    st.code(out["stdout"], language="text")
                    st.warning(
                        "**Still failed on LeetCode?** Paste the LeetCode error below — "
                        "it will be automatically sent to the fix loop."
                    )
                    lc_error = st.text_area(
                        "LeetCode error output:",
                        height=100,
                        key="leetcode_error_after_success",
                        placeholder="e.g.  NameError: name 'Solution' is not defined\n      Wrong Answer: expected [3,4] got [-1,-1]",
                        label_visibility="collapsed",
                    )
                    if st.button("🔧 Fix with LeetCode Error", key="fix_from_lc_success", use_container_width=True):
                        if lc_error.strip():
                            st.session_state.execution_output = None
                            st.session_state.attempt_errors.append(lc_error.strip())
                            st.session_state.attempt_errors = st.session_state.attempt_errors[-3:]
                            _trigger_fix_loop(problem_text, st.session_state.attempt_errors, user_gemini_key)
                        else:
                            st.warning("Paste the LeetCode error first.")
                elif out["stderr"].strip():
                    st.error("❌ Execution failed (local environment).")
                    st.code(out["stderr"], language="text")
                    if st.button("🔧 Send Error to Fix Loop", key="auto_send_error"):
                        st.session_state.execution_output = None
                        st.session_state.attempt_errors.append(out["stderr"].strip())
                        st.session_state.attempt_errors = st.session_state.attempt_errors[-3:]
                        _trigger_fix_loop(problem_text, st.session_state.attempt_errors, user_gemini_key)
                else:
                    st.warning("Code ran but produced no output. Your solution may need explicit print() calls.")

    # --- Manual Error Fix Section ---
    with st.expander("🐛 Paste a LeetCode error to fix the solution"):
        st.caption(
            "Paste any error directly from LeetCode — Wrong Answer, Runtime Error, Time Limit Exceeded. "
            "The AI uses the exact real error to fix the code, not a simulated one."
        )
        error_input = st.text_area(
            "LeetCode error output:",
            height=120,
            key="error_input_box",
            label_visibility="collapsed",
            placeholder="e.g.  Wrong Answer\n      Input: nums = [5,7,7,8,8,10], target = 6\n      Expected: [3,4]\n      Got: [-1,-1]",
        )
        if st.button("🔧 Fix My Solution", type="primary", use_container_width=True):
            if not error_input.strip():
                st.warning("Paste your error output first.")
            else:
                st.session_state.attempt_errors.append(error_input.strip())
                st.session_state.attempt_errors = st.session_state.attempt_errors[-3:]
                _trigger_fix_loop(problem_text, st.session_state.attempt_errors, user_gemini_key)
