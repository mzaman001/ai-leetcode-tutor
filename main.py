import streamlit as st
import re
import os
import uuid
from dotenv import load_dotenv
from database import init_db, save_lesson_to_db, remove_lesson_from_db, get_lessons_context
from executor import execute_code
from ai_client import (
    call_ai, check_guardrail, build_solve_prompt, 
    build_harness_prompt, build_fix_prompt,
    _init_clients, BOUNCER_MODEL, GROQ_FAST_MODEL, get_clients
)

load_dotenv()
init_db()

st.set_page_config(page_title="CodeUnfold", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

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


# Initialize AI clients on start
_default_gemini, _groq_client = _init_clients()
if not _default_gemini:
    st.warning("⚠️ `GEMINI_API_KEY` environment variable is not set.")
    st.stop()


# ---------- Session State ----------
_defaults = {
    "problem_text": "",
    "current_solution": None,
    "current_hints": None,
    "raw_code": "",
    "show_update_alert": False,
    "lesson_saved": False,
    "last_saved_lesson_text": "",
    "attempt_errors": [],
    "execution_output": None,
    "language": "Python",
}
for key, default in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

if "ai_limiter" not in st.session_state:
    from rate_limiter import RateLimiter
    st.session_state.ai_limiter = RateLimiter(max_calls=15, window_seconds=60)
    st.session_state.exec_limiter = RateLimiter(max_calls=10, window_seconds=60)

def _sync_problem():
    new_text = st.session_state._problem_widget
    if new_text != st.session_state.problem_text:
        st.session_state.problem_text = new_text
        st.session_state.current_solution = None
        st.session_state.current_hints = None
        st.session_state.raw_code = ""
        st.session_state.attempt_errors = []
        st.session_state.lesson_saved = False
        st.session_state.execution_output = None

def _trigger_fix_loop(prob_text: str, errors: list, user_key: str = None):
    error_history = "\n".join(f"Error #{i + 1}:\n{e}" for i, e in enumerate(errors))
    code_to_fix = st.session_state.raw_code or "(code unavailable)"
    
    fix_prompt = build_fix_prompt(
        prob_text, code_to_fix, error_history, 
        st.session_state.language, get_lessons_context()
    )
    
    if not st.session_state.ai_limiter.allow():
        st.error("Too many requests! Please wait a moment.")
        return

    with st.spinner("Analyzing error and generating fix..."):
        try:
            new_text = call_ai(fix_prompt, user_key)
            # Extract the main solution code robustly
            code_section_match = re.search(r"4\. The Code.*?```(?:\w+)?\n(.*?)```", new_text, re.DOTALL | re.IGNORECASE)
            if code_section_match:
                st.session_state.raw_code = code_section_match.group(1).strip()
            else:
                matches = re.findall(r"```(?:\w+)?\n(.*?)```", new_text, re.DOTALL | re.IGNORECASE)
                st.session_state.raw_code = max(matches, key=len).strip() if matches else ""
            
            st.session_state.current_solution = new_text
            st.session_state.show_update_alert = True
            st.session_state.execution_output = None
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred: {e}")


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### 🌐 Language")
    st.session_state.language = st.selectbox(
        "Choose your interview language:",
        ["Python", "JavaScript", "Java", "C++", "Go", "Rust"]
    )
    
    if st.session_state.language not in ["Python", "JavaScript"]:
        st.caption(f"Note: Local 'Run Code' execution is not available for {st.session_state.language}. Only the Tutor is available.")

    st.markdown("### ⚙️ API Settings")
    st.markdown("Add your own key to bypass free-tier rate limits.")
    user_gemini_key = st.text_input("Your Gemini API Key (Optional)", type="password")
    if user_gemini_key:
        st.success("Using your personal Gemini key!")
    st.divider()

    st.markdown("### 🧠 Persistent Memory")
    # Show recently saved from DB
    context = get_lessons_context()
    if context:
        st.caption("Lessons saved in local SQLite DB:")
        lessons = [line.strip("- ") for line in context.split("\n") if line.startswith("- ")]
        for l in lessons[:3]:
            st.caption(f"• {l[:70]}{'...' if len(l) > 70 else ''}")
    else:
        st.caption("No lessons yet. Verify a correct solution to build memory!")


# ---------- Main UI ----------
st.title("CodeUnfold")
st.markdown("Paste any coding problem below. Get **hints** to solve it yourself, or **reveal the full solution** for a complete step-by-step lesson.")

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


if hint_button and problem_text:
    if not st.session_state.ai_limiter.allow():
        st.error("Too many requests! Please wait a moment.")
        st.stop()
        
    with st.spinner("Checking input..."):
        if not check_guardrail(problem_text, user_gemini_key):
            st.session_state.current_solution = None
            st.session_state.current_hints = None
            st.warning("That doesn't look like a coding problem. Please paste a valid programming question.")
            st.stop()

    hint_prompt = f"""You are a LeetCode Grandmaster and patient tutor. The student wants to solve this themselves in {st.session_state.language} — give hints ONLY. No code.
<user_problem>
{problem_text}
</user_problem>
1. What's This Problem Really Asking?
2. Concepts You'll Need
3. Step-by-Step Thinking Path
4. Common Pitfalls
CRITICAL: Do NOT write any code."""
    try:
        with st.spinner("Thinking through hints..."):
            result = call_ai(hint_prompt, user_gemini_key)
        st.session_state.current_hints = result
        st.session_state.current_solution = None
        st.rerun()
    except Exception as e:
        st.error(f"An error occurred: {e}")

elif solve_button and problem_text:
    if not st.session_state.ai_limiter.allow():
        st.error("Too many requests! Please wait a moment.")
        st.stop()

    with st.spinner("Checking input..."):
        if not check_guardrail(problem_text, user_gemini_key):
            st.session_state.current_solution = None
            st.session_state.current_hints = None
            st.warning("That doesn't look like a coding problem. Please paste a valid programming question.")
            st.stop()

    st.session_state.attempt_errors = []
    st.session_state.lesson_saved = False

    solve_prompt = build_solve_prompt(problem_text, st.session_state.language, get_lessons_context())
    
    try:
        with st.spinner(f"Generating {st.session_state.language} lesson..."):
            result = call_ai(solve_prompt, user_gemini_key)

        result = re.sub(r"<scratchpad>.*?</scratchpad>", "", result, flags=re.IGNORECASE | re.DOTALL)
        
        # Extract the main solution code robustly
        code_section_match = re.search(r"4\. The Code.*?```(?:\w+)?\n(.*?)```", result, re.DOTALL | re.IGNORECASE)
        if code_section_match:
            st.session_state.raw_code = code_section_match.group(1).strip()
        else:
            matches = re.findall(r"```(?:\w+)?\n(.*?)```", result, re.DOTALL | re.IGNORECASE)
            st.session_state.raw_code = max(matches, key=len).strip() if matches else ""

        st.session_state.current_solution = result.strip()
        st.session_state.current_hints = None
        st.session_state.show_update_alert = False
        st.session_state.lesson_saved = False
        st.rerun()
    except Exception as e:
        st.error(f"An error occurred: {e}")


# ---------- Display Hints ----------
if st.session_state.current_hints and not st.session_state.current_solution:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**Problem:** {problem_text[:80]}...")
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("### 💡 Hints & Strategy")
        st.write(st.session_state.current_hints)


# ---------- Display Solution + Fix Loop ----------
if st.session_state.current_solution:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**Problem:** {problem_text[:80]}...")

    with st.chat_message("assistant", avatar="🤖"):
        st.html('<script>setTimeout(function(){ window.parent.document.querySelector("section.main").scrollTo({top: 0, behavior: "smooth"}); }, 150);</script>')

        if st.session_state.show_update_alert:
            st.success("Solution updated based on your error report.")
            st.session_state.show_update_alert = False

        st.markdown("### Solution Breakdown")
        st.write(st.session_state.current_solution)

        error_count = len(st.session_state.attempt_errors)
        if error_count > 0:
            st.caption(f"🔄 Revised {error_count} time(s) based on your feedback.")

        # Save Memory
        if st.session_state.get("lesson_saved", False):
            st.success("✅ Saved to local SQLite database!", icon="🧠")
            if st.button("Undo (Remove from Memory)"):
                last = st.session_state.get("last_saved_lesson_text", "")
                remove_lesson_from_db(last)
                st.session_state.lesson_saved = False
                st.rerun()
        else:
            if "save_toggle_key" not in st.session_state:
                st.session_state.save_toggle_key = f"save_toggle_{uuid.uuid4().hex[:8]}"
            toggle_key = st.session_state.save_toggle_key
            show_save = st.toggle("💾 Save this approach to memory", key=toggle_key)
            if show_save:
                proof_text = st.text_area("Paste your execution output:", height=68, key="proof_input")
                if st.button("Verify & Save", use_container_width=True, type="primary"):
                    if not proof_text or len(proof_text.strip()) < 3:
                        st.error("Please provide actual proof of execution.")
                    elif not _groq_client:
                        st.error("Groq API key required for Bouncer AI.")
                    else:
                        safe_code = (st.session_state.raw_code or st.session_state.current_solution)[:3000]
                        bouncer_prompt = (
                            f"You are a strict Bouncer AI. A student claims a {st.session_state.language} solution worked.\n"
                            f'Proof: "{proof_text[:500]}"\n\n'
                            f"Rules:\n"
                            f"1. If proof is fake/troll, output: REJECT\n"
                            f"2. If proof looks real, extract a 1-sentence lesson wrapped in <LESSON> tags.\n\n"
                            f"Problem: <user_problem>{problem_text[:800]}</user_problem>\n"
                            f"Code:\n```{st.session_state.language.lower()}\n{safe_code}\n```"
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
                                    st.error("🛑 Bouncer Rejected: That doesn't look like real execution output.")
                                else:
                                    m = re.search(r"<LESSON>(.*?)</LESSON>", reply, re.IGNORECASE | re.DOTALL)
                                    lesson = "✅ PROVEN: " + (m.group(1).strip() if m else "Solution approach verified working.")
                                    save_lesson_to_db(lesson)
                                    st.session_state.last_saved_lesson_text = lesson
                                    st.session_state.lesson_saved = True
                                    st.balloons()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Bouncer AI error: {e}")

        # Run Code
        if st.session_state.raw_code and st.session_state.language in ["Python", "JavaScript"]:
            with st.expander("▶ Run Code — Quick Sanity Check", expanded=bool(st.session_state.execution_output)):
                st.info("⚠️ **This is a local sanity check only.** Passing here does **not** guarantee the code will pass on LeetCode.")
                if st.button("▶ Run Code", type="primary", use_container_width=True, key="run_code_btn"):
                    if not st.session_state.exec_limiter.allow():
                        st.error("Too many execution requests! Please wait a moment.")
                        st.stop()
                    
                    harness_prompt = build_harness_prompt(problem_text, st.session_state.raw_code, st.session_state.language)
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

                            runnable_code = re.sub(r"^```(?:python|javascript|js)?\n?", "", runnable_code.strip(), flags=re.MULTILINE|re.IGNORECASE)
                            runnable_code = re.sub(r"\n?```$", "", runnable_code.strip(), flags=re.MULTILINE)

                            result = execute_code(runnable_code, language=st.session_state.language)
                            st.session_state.execution_output = result
                            st.rerun()
                        except Exception as e:
                            st.session_state.execution_output = {"stdout": "", "stderr": str(e), "success": False}
                            st.rerun()

                if st.session_state.execution_output:
                    out = st.session_state.execution_output
                    if out["success"] and out["stdout"].strip():
                        st.success("✅ Passed local sanity check")
                        st.code(out["stdout"], language="text")
                        st.warning("**Still failed on LeetCode?** Paste the LeetCode error below — it will be automatically sent to the fix loop.")
                        lc_error = st.text_area("LeetCode error output:", height=100, key="lc_error_after_success", label_visibility="collapsed")
                        if st.button("🔧 Fix with LeetCode Error", key="fix_from_lc", use_container_width=True):
                            if lc_error.strip():
                                st.session_state.attempt_errors.append(lc_error.strip())
                                st.session_state.attempt_errors = st.session_state.attempt_errors[-3:]
                                _trigger_fix_loop(problem_text, st.session_state.attempt_errors, user_gemini_key)
                            else:
                                st.warning("Paste the LeetCode error first.")
                    elif out["stderr"].strip():
                        st.error("❌ Execution failed (local environment).")
                        st.code(out["stderr"], language="text")
                        if st.button("🔧 Send Error to Fix Loop", key="auto_send_error"):
                            st.session_state.attempt_errors.append(out["stderr"].strip())
                            st.session_state.attempt_errors = st.session_state.attempt_errors[-3:]
                            _trigger_fix_loop(problem_text, st.session_state.attempt_errors, user_gemini_key)
                    else:
                        st.warning("Code ran but produced no output.")

        # Manual Fix Expander
        with st.expander("🐛 Paste a LeetCode error to fix the solution"):
            st.caption("Paste any error directly from LeetCode. The AI uses the exact real error to fix the code.")
            error_input = st.text_area("LeetCode error output:", height=120, key="error_input_box", label_visibility="collapsed")
            if st.button("🔧 Fix My Solution", type="primary", use_container_width=True):
                if not error_input.strip():
                    st.warning("Paste your error output first.")
                else:
                    st.session_state.attempt_errors.append(error_input.strip())
                    st.session_state.attempt_errors = st.session_state.attempt_errors[-3:]
                    _trigger_fix_loop(problem_text, st.session_state.attempt_errors, user_gemini_key)
