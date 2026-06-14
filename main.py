import streamlit as st
import re
import os
import uuid
import time
import difflib
from dotenv import load_dotenv
from logger import log
from ai_client import (
    call_ai, build_solve_prompt, 
    build_fix_prompt, _sanitize_input,
    build_pedagogical_hint_prompt, build_code_review_prompt,
    GROQ_FAST_MODEL, get_clients
)

load_dotenv()

st.set_page_config(page_title="CodeUnfold", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# ---------- CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Inter:wght@400;500;600&display=swap');

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
    ::selection { background: rgba(245, 158, 11, 0.3); color: #f8fafc; }
    section.main { overflow-anchor: none !important; }

    /* Typography Hierarchy */
    h1, h2, h3, p, li, label { font-family: 'Inter', -apple-system, sans-serif !important; }

    .stTextArea textarea {
        background-color: #1e293b !important; border: 2px solid #334155 !important;
        color: #f8fafc !important; font-family: 'Fira Code', monospace !important;
        border-radius: 12px !important; padding: 16px !important; font-size: 14px !important;
        transition: all 0.3s ease !important; box-shadow: none !important;
    }
    .stTextArea textarea:focus { border-color: #f59e0b !important; box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1) !important; }
    
    [data-testid="stExpander"] { background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 12px !important; margin-bottom: 12px !important; }
    [data-testid="stExpander"] summary { font-family: 'Inter', sans-serif !important; font-weight: 600 !important; color: #f8fafc !important; }
    
    .stButton > button { border-radius: 12px !important; padding: 12px 32px !important; font-weight: 600 !important; border: none !important; transition: all 0.2s ease !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #f59e0b, #f97316) !important; color: #000 !important; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3) !important; }
    .stButton > button[kind="primary"]:hover { transform: translateY(-1px) !important; box-shadow: 0 6px 16px rgba(245, 158, 11, 0.4) !important; }
    .stButton > button[kind="secondary"] { background: rgba(59, 130, 246, 0.1) !important; border: 1px solid rgba(59, 130, 246, 0.3) !important; color: #93c5fd !important; }
    
    [data-testid="stChatMessage"] { background: #1e293b !important; border: 1px solid #334155 !important; border-left: 4px solid #f59e0b !important; border-radius: 12px !important; padding: 24px !important; box-shadow: none !important; margin-bottom: 16px !important; }
    [data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) { border-left-color: #64748b !important; }
    
    pre { background: #0f172a !important; border: 1px solid #334155 !important; border-radius: 8px !important; padding: 20px !important; }
    pre code { font-family: 'Fira Code', monospace !important; font-size: 13px !important; color: #f8fafc !important; }
    
    section[data-testid="stSidebar"] { background: #0f172a !important; border-right: 1px solid #334155 !important; }

    /* Animated Spinners */
    @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
    .stSpinner > div > div > div { animation: pulse 1.5s ease-in-out infinite !important; }

    /* Typography Hierarchy */
    .markdown-text-container h2 {
        border-left: 4px solid #f59e0b !important;
        padding-left: 12px !important;
        background: rgba(245, 158, 11, 0.05);
        padding-top: 4px !important;
        padding-bottom: 4px !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
        font-size: 1.4rem !important;
    }
    .markdown-text-container h3 {
        font-family: 'Fira Code', monospace !important;
        font-size: 1.2rem !important;
        color: #e2e8f0 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.8rem !important;
    }

    /* Mobile Responsive */
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
        [data-testid="stChatMessage"] { padding: 12px 16px !important; }
        .stTextArea textarea { min-height: 100px !important; }
    }
</style>
""", unsafe_allow_html=True)


SESSION_AI_CALL_LIMIT = 5

def _check_session_limit(user_key: str = None) -> bool:
    if user_key:
        return True # Unlimited if they provide their own key
    return st.session_state.get("session_ai_calls", 0) < SESSION_AI_CALL_LIMIT

def _increment_session_calls():
    st.session_state.session_ai_calls = st.session_state.get("session_ai_calls", 0) + 1

def _show_session_limit_warning(user_key: str = None):
    if user_key:
        return
    used = st.session_state.get("session_ai_calls", 0)
    remaining = SESSION_AI_CALL_LIMIT - used
    if remaining <= 2:
        st.info(
            f"💡 **{remaining} free AI call{'s' if remaining != 1 else ''} remaining** this session. "
            "Add your own free Gemini API key in ⚙️ **Settings** (sidebar) for unlimited access."
        )

def _get_lessons_context() -> str:
    """Retrieves recent lessons from ephemeral session state."""
    lessons = st.session_state.get("lessons_memory", [])
    if not lessons:
        return ""
    # Reverse to put oldest first among the 5 recent
    recent_lessons = list(reversed(lessons[-5:]))
    return "\n\nLESSONS FROM YOUR MEMORY (avoid repeating past mistakes):\n" + "\n".join(f"- {l}" for l in recent_lessons)

def _show_error(e: Exception, context: str = ""):
    err = str(e).lower()
    if "rate" in err or "429" in err or "resource_exhausted" in err:
        st.error("⏳ Rate limit reached. Please wait a moment and try again.")
    elif "503" in err or "unavailable" in err or "busy" in err:
        st.error("🔄 AI is temporarily under high load. Please try again in 10–15 seconds.")
    elif "timeout" in err:
        st.error("⏱️ Request timed out. Please try again.")
    elif "api" in err or "key" in err or "auth" in err:
        st.error("🔑 API key issue. Please check your API keys in the sidebar.")
    else:
        st.error("❌ Something went wrong. Please try again.")
        log.error(f"{context}: {e}")


# Initialize AI clients on start
_default_gemini, _groq_client = get_clients()

if not _default_gemini and not _groq_client:
    st.error("🔑 No API keys configured. The app can't function without at least one.")
    st.markdown("""
    **Get a free Groq key in 30 seconds (recommended):**
    1. Go to [console.groq.com](https://console.groq.com)
    2. Sign in → Create API Key → Copy it
    3. Paste it below or add it to your `.env` file as `GROQ_API_KEY`
    """)
    user_key_setup = st.text_input("Paste your Groq or Gemini API key here to continue:", type="password")
    st.stop()
elif not _default_gemini:
    st.sidebar.warning("⚠️ Gemini key not set. Using Groq only.")
elif not _groq_client:
    st.sidebar.warning("⚠️ Groq key not set. Using Gemini only (slower).")


# ---------- Session State ----------
_defaults = {
    "problem_text": "",
    "current_solution": None,
    "current_hints": None,
    "raw_code": "",
    "show_update_alert": False,
    "lesson_saved": False,
    "last_saved_lesson_text": "",
    "last_saved_lesson_id": -1,
    "attempt_errors": [],
    "execution_output": None,
    "language": "Python",
    "user_code": "",
}
for key, default in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

if "ai_limiter" not in st.session_state:
    from rate_limiter import RateLimiter
    st.session_state.ai_limiter = RateLimiter(max_calls=15, window_seconds=60)
    st.session_state.session_ai_calls = 0  # Per-visitor cap counter
    st.session_state.lessons_memory = []  # Ephemeral memory for this session

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
        st.session_state.user_code = ""

def _sync_language():
    st.session_state.current_solution = None
    st.session_state.current_hints = None
    st.session_state.raw_code = ""
    st.session_state.attempt_errors = []
    st.session_state.lesson_saved = False
    st.session_state.execution_output = None
    st.session_state.user_code = ""

def _trigger_fix_loop(prob_text: str, errors: list, user_key: str = None):
    error_history = "\n".join(f"Error #{i + 1}:\n{e}" for i, e in enumerate(errors))
    code_to_fix = st.session_state.raw_code or "(code unavailable)"
    
    fix_prompt = build_fix_prompt(
        prob_text, code_to_fix, error_history, 
        st.session_state.language, _get_lessons_context()
    )
    
    if not st.session_state.ai_limiter.allow():
        st.error("Too many requests! Please wait a moment.")
        return

    with st.spinner("Analyzing error and generating fix..."):
        try:
            old_code = st.session_state.raw_code
            t0 = time.time()
            new_text = call_ai(fix_prompt, user_key)
            t1 = time.time()
            
            # Extract the main solution code robustly via XML tags
            code_match = re.search(r"<code>(.*?)</code>", new_text, re.DOTALL | re.IGNORECASE)
            if code_match:
                matches = re.findall(r"```(?:\w+)?\n(.*?)```", code_match.group(1), re.DOTALL | re.IGNORECASE)
                st.session_state.raw_code = max(matches, key=len).strip() if matches else ""
            else:
                matches = re.findall(r"```(?:\w+)?\n(.*?)```", new_text, re.DOTALL | re.IGNORECASE)
                st.session_state.raw_code = max(matches, key=len).strip() if matches else ""
            
            if old_code and st.session_state.raw_code:
                diff = list(difflib.unified_diff(
                    old_code.splitlines(), 
                    st.session_state.raw_code.splitlines(), 
                    fromfile='Previous Code', 
                    tofile='Fixed Code', 
                    lineterm=''
                ))
                if diff:
                    diff_text = "\n".join(diff)
                    diff_markdown = f"### 🔍 Code Diff (What Changed)\n```diff\n{diff_text}\n```\n\n---\n\n"
                    # Inject diff into problem_statement tag so it renders in the Overview tab
                    if "<problem_statement>" in new_text:
                        new_text = re.sub(r"(<problem_statement>)", r"\1\n" + diff_markdown, new_text, flags=re.IGNORECASE)
                    else:
                        new_text = diff_markdown + new_text

            new_text = new_text + f"\n\n---\n*⏱️ Fix generated in {t1-t0:.1f}s*"
            st.session_state.current_solution = new_text
            st.session_state.show_update_alert = True
            st.session_state.execution_output = None
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred: {e}")


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🤖 CodeUnfold")
    st.caption("AI-Powered LeetCode Tutor")
    st.divider()

    st.markdown("### ⚡ API Status")
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        if _groq_client:
            st.success("Groq ✓")
        else:
            st.error("Groq ✗")
    with status_col2:
        if _default_gemini:
            st.success("Gemini ✓")
        else:
            st.error("Gemini ✗")
    
    st.divider()

    st.radio("UI Theme", ["AMOLED", "Deep Dark"], key="theme", horizontal=True)

    with st.expander("🔑 API Settings", expanded=False):
        user_gemini_key = st.text_input("Your Gemini API Key (Optional)", type="password")
        if user_gemini_key:
            st.toast("Using your personal Gemini key!", icon="✅")
    
    with st.expander("🧠 Session Memory", expanded=True):
        st.caption("Lessons save for this session. Persist longer by self-hosting.")
        context = _get_lessons_context()
        if context:
            lessons = [line.strip("- ") for line in context.split("\n") if line.startswith("- ")]
            for l in lessons[:5]:
                st.caption(f"• {l[:60]}{'...' if len(l) > 60 else ''}")
        else:
            st.caption("No lessons yet.")

# ---------- Dynamic CSS Injection ----------
bg_color = "#000000" if st.session_state.get("theme") == "AMOLED" else "#0f172a"
sidebar_bg = "#000000" if st.session_state.get("theme") == "AMOLED" else "#1e293b"

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_color} !important; transition: background-color 0.3s; }}
    section[data-testid="stSidebar"] {{ background-color: {sidebar_bg} !important; border-right: 1px solid #1a1a24 !important; }}
</style>
""", unsafe_allow_html=True)


# ---------- Main UI ----------
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.markdown("# 🤖 CodeUnfold")
with header_col2:
    st.selectbox(
        "Language", ["Python", "JavaScript", "Java", "C++", "Go", "Rust"],
        key="language",
        on_change=_sync_language,
        label_visibility="collapsed"
    )
    if st.session_state.language not in ["Python", "JavaScript"]:
        st.caption("No local run support")

st.markdown("### Problem Input")
with st.form("input_form"):
    st.text_area(
        "Paste your coding problem here:",
        height=150,
        max_chars=5000,
        key="_problem_widget",
        placeholder="Paste problem description + starter code template...\n\nTip: Include both the problem AND the starter code for best results.",
        label_visibility="collapsed"
    )

    st.text_area(
        "Your Current Code (Optional):",
        height=150,
        max_chars=5000,
        key="user_code",
        placeholder="Paste your current attempt here if you want a code review instead of generic hints...",
        label_visibility="visible"
    )

    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        hint_button = st.form_submit_button("💡 Get Hints", use_container_width=True, type="secondary")
    with btn_col2:
        solve_button = st.form_submit_button("🔍 Reveal Solution", use_container_width=True, type="primary")

# Manual state sync when form is submitted
if hint_button or solve_button:
    new_text = st.session_state._problem_widget
    if new_text != st.session_state.problem_text:
        st.session_state.problem_text = new_text
        st.session_state.current_solution = None
        st.session_state.current_hints = None
        st.session_state.raw_code = ""
        st.session_state.attempt_errors = []
        st.session_state.lesson_saved = False
        st.session_state.execution_output = None

problem_text = st.session_state.problem_text

# ---------- Onboarding Welcome ----------
if not problem_text:
    st.markdown("---")
    st.markdown("### 👋 Welcome to CodeUnfold")
    st.markdown("""
    **How it works:**
    1. Paste any LeetCode problem — include the starter code template for best results
    2. Click **Get Hints** to get guided nudges and solve it yourself
    3. Click **Reveal Solution** for a full step-by-step lesson with analogies
    4. Save proven approaches to session memory
    """)
    st.markdown("### 🚀 Try it now with an example")
    ex_col1, ex_col2 = st.columns(2)
    with ex_col1:
        if st.button("🔢 Two Sum", use_container_width=True):
            _text = """Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice.

Example: Input: nums = [2,7,11,15], target = 9 -> Output: [0,1]

class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:"""
            st.session_state.problem_text = _text
            st.session_state["_problem_widget"] = _text
            st.rerun()
    with ex_col2:
        if st.button("💞 Valid Parentheses", use_container_width=True):
            _text = """Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid. An input string is valid if open brackets are closed by the same type of brackets, and in the correct order.

Example: Input: s = "()[]{}" -> Output: true

class Solution:
    def isValid(self, s: str) -> bool:"""
            st.session_state.problem_text = _text
            st.session_state["_problem_widget"] = _text
            st.rerun()


if hint_button and problem_text:
    log.info(f"User Action: Request Hint - Language: {st.session_state.language}")
    if st.session_state.current_hints:
        st.rerun()  # Already generated, just display
    if not _check_session_limit(user_gemini_key):
        st.warning(f"💡 You've used all {SESSION_AI_CALL_LIMIT} free AI calls for this session. Add your own free Gemini API key in ⚙️ **Settings** in the sidebar for unlimited access.")
        st.stop()
    if not st.session_state.ai_limiter.allow():
        st.error("⏳ Too many requests! Please wait a moment.")
        st.stop()
    _show_session_limit_warning()
        
    if st.session_state.user_code and len(st.session_state.user_code.strip()) > 5:
        hint_prompt = build_code_review_prompt(problem_text, st.session_state.user_code, st.session_state.language)
        spinner_msg = "Reviewing your code..."
    else:
        hint_prompt = build_pedagogical_hint_prompt(problem_text, st.session_state.language)
        spinner_msg = "Analyzing problem and generating hints..."
        
    try:
        with st.spinner(spinner_msg):
            t0 = time.time()
            result = call_ai(hint_prompt, user_gemini_key)
            t1 = time.time()
                
        result += f"\n\n---\n*⏱️ Hints generated in {t1-t0:.1f}s*"
        _increment_session_calls()
        st.session_state.current_hints = result
        st.session_state.current_solution = None
        st.rerun()
    except Exception as e:
        _show_error(e, "hint generation")

elif solve_button and problem_text:
    log.info(f"User Action: Reveal Solution - Language: {st.session_state.language}")
    if st.session_state.current_solution:
        st.rerun()  # Already generated, just display
    if not _check_session_limit(user_gemini_key):
        st.warning(f"💡 You've used all {SESSION_AI_CALL_LIMIT} free AI calls for this session. Add your own free Gemini API key in ⚙️ **Settings** in the sidebar for unlimited access.")
        st.stop()
    if not st.session_state.ai_limiter.allow():
        st.error("⏳ Too many requests! Please wait a moment.")
        st.stop()

    st.session_state.attempt_errors = []
    st.session_state.lesson_saved = False

    solve_prompt = build_solve_prompt(problem_text, st.session_state.language, _get_lessons_context())
    
    try:
        with st.spinner(f"Generating {st.session_state.language} lesson..."):
            t0 = time.time()
            result = call_ai(solve_prompt, user_gemini_key)
            t1 = time.time()

        result = result + f"\n\n---\n*⏱️ Lesson generated in {t1-t0:.1f}s*"
        _increment_session_calls()
        st.session_state.current_solution = result
        st.session_state.current_hints = None
        
        # Extract the main solution code robustly
        code_match = re.search(r"<code>(.*?)</code>", result, re.DOTALL | re.IGNORECASE)
        if code_match:
            matches = re.findall(r"```(?:\w+)?\n(.*?)```", code_match.group(1), re.DOTALL | re.IGNORECASE)
            st.session_state.raw_code = max(matches, key=len).strip() if matches else ""
        else:
            matches = re.findall(r"```(?:\w+)?\n(.*?)```", result, re.DOTALL | re.IGNORECASE)
            st.session_state.raw_code = max(matches, key=len).strip() if matches else ""

        st.session_state.current_solution = result.strip()
        st.session_state.current_hints = None
        st.session_state.show_update_alert = False
        st.session_state.lesson_saved = False
        st.rerun()
    except Exception as e:
        _show_error(e, "solution generation")


# ---------- Display Hints ----------
if st.session_state.current_hints and not st.session_state.current_solution:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**Problem:** {problem_text[:80]}...")
    with st.chat_message("assistant", avatar="🤖"):
        hints_text = st.session_state.current_hints
        critique_match = re.search(r"<critique>(.*?)</critique>", hints_text, re.DOTALL | re.IGNORECASE)
        logic_flaw_match = re.search(r"<logic_flaw>(.*?)</logic_flaw>", hints_text, re.DOTALL | re.IGNORECASE)
        fix_direction_match = re.search(r"<fix_direction>(.*?)</fix_direction>", hints_text, re.DOTALL | re.IGNORECASE)
        
        intuition_match = re.search(r"<intuition>(.*?)</intuition>", hints_text, re.DOTALL | re.IGNORECASE)
        walkthrough_match = re.search(r"<walkthrough>(.*?)</walkthrough>", hints_text, re.DOTALL | re.IGNORECASE)
        pseudocode_match = re.search(r"<pseudocode>(.*?)</pseudocode>", hints_text, re.DOTALL | re.IGNORECASE)
        
        if critique_match and logic_flaw_match and fix_direction_match:
            st.markdown("### 🧑‍💻 Code Review")
            tab1, tab2, tab3 = st.tabs(["🔍 Critique", "🧠 Logic Flaw", "🏗️ Fix Direction"])
            with tab1:
                st.markdown(critique_match.group(1).strip())
            with tab2:
                st.markdown(logic_flaw_match.group(1).strip())
            with tab3:
                st.markdown(fix_direction_match.group(1).strip())
        elif intuition_match and walkthrough_match and pseudocode_match:
            st.markdown("### 💡 Hints & Strategy")
            tab1, tab2, tab3 = st.tabs(["🧠 Intuition", "🚶 Walkthrough", "🏗️ Pseudo-code"])
            with tab1:
                st.markdown(intuition_match.group(1).strip())
            with tab2:
                st.markdown(walkthrough_match.group(1).strip())
            with tab3:
                st.markdown(pseudocode_match.group(1).strip())
        else:
            # Fallback if AI failed to format properly
            st.write(hints_text)

# ---------- Display Solution + Fix Loop ----------
if st.session_state.current_solution:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**Problem:** {problem_text[:80]}...")

    with st.chat_message("assistant", avatar="🤖"):
        if st.session_state.show_update_alert:
            st.success("Solution updated based on your error report.")
            st.session_state.show_update_alert = False

        st.markdown("### Solution Breakdown")
        sol_text = st.session_state.current_solution
        
        prob_match = re.search(r"<problem_statement>(.*?)</problem_statement>", sol_text, re.DOTALL | re.IGNORECASE)
        key_match = re.search(r"<key_idea>(.*?)</key_idea>", sol_text, re.DOTALL | re.IGNORECASE)
        app_match = re.search(r"<approach>(.*?)</approach>", sol_text, re.DOTALL | re.IGNORECASE)
        code_match = re.search(r"<code>(.*?)</code>", sol_text, re.DOTALL | re.IGNORECASE)
        exp_match = re.search(r"<explanation>(.*?)</explanation>", sol_text, re.DOTALL | re.IGNORECASE)
        comp_match = re.search(r"<complexity>(.*?)</complexity>", sol_text, re.DOTALL | re.IGNORECASE)
        take_match = re.search(r"<takeaway>(.*?)</takeaway>", sol_text, re.DOTALL | re.IGNORECASE)
        
        if prob_match and key_match and app_match and code_match and exp_match and comp_match and take_match:
            s_tab1, s_tab2, s_tab3, s_tab4 = st.tabs(["📖 Overview", "🧠 Logic", "💻 Code", "💡 Takeaway"])
            with s_tab1:
                st.markdown(prob_match.group(1).strip())
                st.markdown(key_match.group(1).strip())
            with s_tab2:
                st.markdown(app_match.group(1).strip())
                st.markdown(comp_match.group(1).strip())
            with s_tab3:
                st.markdown(code_match.group(1).strip())
                st.markdown(exp_match.group(1).strip())
            with s_tab4:
                st.markdown(take_match.group(1).strip())
        else:
            st.write(sol_text)

        error_count = len(st.session_state.attempt_errors)
        if error_count > 0:
            st.caption(f"🔄 Revised {error_count} time(s) based on your feedback.")

        # Save Memory
        if st.session_state.get("lesson_saved", False):
            st.success("✅ Saved to session memory!", icon="🧠")
            if st.button("Undo (Remove from Memory)"):
                if st.session_state.lessons_memory:
                    st.session_state.lessons_memory.pop()
                st.session_state.lesson_saved = False
                st.rerun()
        else:
            if st.button("💾 Save this approach to memory", use_container_width=True):
                sol_text = st.session_state.current_solution
                take_match = re.search(r"<takeaway>(.*?)</takeaway>", sol_text, re.DOTALL | re.IGNORECASE)
                takeaway_text = take_match.group(1).strip() if take_match else "Saved solution approach."
                
                # Prepend the problem title (first line of problem text) to give context
                title = problem_text.split('\n')[0][:50] if problem_text else "Unknown Problem"
                lesson = f"{title}: {takeaway_text}"
                
                st.session_state.lessons_memory.append(lesson)
                st.session_state.lesson_saved = True
                st.balloons()
                st.rerun()

        # Manual Fix Expander
        with st.expander("🐛 Paste a LeetCode error to fix the solution"):
            st.caption("Paste any error directly from LeetCode. The AI uses the exact real error to fix the code.")
            error_input = st.text_area("LeetCode error output:", height=120, key="error_input_box", label_visibility="collapsed")
            if st.button("🔧 Fix My Solution", type="primary", use_container_width=True):
                log.info("User Action: Submit LeetCode Error")
                if not error_input.strip():
                    st.warning("Paste your error output first.")
                else:
                    st.session_state.attempt_errors.append(error_input.strip())
                    st.session_state.attempt_errors = st.session_state.attempt_errors[-3:]
                    _trigger_fix_loop(problem_text, st.session_state.attempt_errors, user_gemini_key)
