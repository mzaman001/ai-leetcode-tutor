import streamlit as st
from google import genai
from google.genai import types
from groq import Groq
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import re

# Load environment variables
load_dotenv()

st.set_page_config(page_title="CodeUnfold", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Inter:wght@400;500;600&display=swap');
    
    /* Global scrollbar styling */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent; 
    }
    ::-webkit-scrollbar-thumb {
        background: #1e293b; 
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #334155; 
    }

    /* Text selection styling */
    ::selection {
        background: rgba(245, 158, 11, 0.3);
        color: #f8fafc;
    }

    /* Minimal Dark Pro Background with Top Accent Bar */
    .stApp {
        background-color: #0a0a0f !important;
        background-image: radial-gradient(ellipse at 50% 0%, rgba(245, 158, 11, 0.04) 0%, transparent 60%) !important;
        background-size: auto !important;
    }
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #f59e0b, #f97316);
        z-index: 999;
    }

    /* Enforce Typography */
    h1, h2, h3, p, li, label {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    
    /* Tech Editor Input (Text Area) */
    .stTextArea textarea {
        background-color: rgba(15, 23, 42, 0.6) !important;
        backdrop-filter: blur(10px);
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
    
    /* Protect Streamlit Icons */
    span[class*="material-symbols"], i[class*="material-symbols"], .material-icons {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }
    
    /* Deep Rich Code Blocks for IDE Feel */
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
    pre code {
        color: #f8fafc !important;
    }
    
    /* Refined Chat Bubbles (Left Accent) */
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
    
    /* Soft Pill Buttons */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        text-transform: none !important;
        letter-spacing: normal !important;
        border-radius: 999px !important;
        padding: 8px 24px !important;
        transition: all 0.2s ease !important;
    }

    /* Hint Button (Secondary - Subtle Dark) */
    .stButton > button[kind="secondary"] {
        background: rgba(245, 158, 11, 0.08) !important;
        border: 1px solid rgba(245, 158, 11, 0.2) !important;
        color: #fcd34d !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(245, 158, 11, 0.15) !important;
        border-color: #f59e0b !important;
        transform: none !important;
        box-shadow: none !important;
    }

    /* Solve Button (Primary) */
    .stButton > button[kind="primary"] {
        background: #f59e0b !important;
        border: none !important;
        color: #000 !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        opacity: 0.9 !important;
        transform: none !important;
        box-shadow: none !important;
    }

    /* Sidebar - Cleaner */
    section[data-testid="stSidebar"] {
        background-color: #0d0d14 !important;
        border-right: 1px solid #1a1a24 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("CodeUnfold")
st.markdown("""
Welcome to your personal AI coding assistant! Paste any coding problem, assignment, or bug below. 
You can choose to get **hints and strategies** to learn and solve it yourself, or **reveal the solution** for a full breakdown.
""")

api_key = os.environ.get("GEMINI_API_KEY")
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not api_key:
    st.warning("⚠️ `GEMINI_API_KEY` is not set.")
    st.stop()

if not supabase_url or not supabase_key:
    st.warning("⚠️ Supabase credentials are not set in `.env`.")
    st.stop()

# Initialize Default Clients
default_ai_client = genai.Client(api_key=api_key)
supabase: Client = create_client(supabase_url, supabase_key)

groq_api_key = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-pro-exp-02-05", "gemini-2.0-flash-lite"]
GROQ_MODEL = "llama-3.3-70b-versatile"
BOUNCER_MODEL = "llama-3.1-8b-instant"

# ---------- UI: Bring Your Own Key ----------
with st.sidebar:
    st.markdown("### API Settings")
    st.markdown("Add your own key to bypass free-tier rate limits.")
    user_gemini_key = st.text_input("Your Gemini API Key (Optional)", type="password")
    if user_gemini_key:
        st.success("Using your personal API key!")
    st.divider()

# ---------- Session State Initialization ----------
# Persist the problem text so it survives st.rerun()
if "problem_text" not in st.session_state:
    st.session_state.problem_text = ""

if "current_solution" not in st.session_state:
    st.session_state.current_solution = None

if "show_update_alert" not in st.session_state:
    st.session_state.show_update_alert = False

if "lesson_saved" not in st.session_state:
    st.session_state.lesson_saved = False

# Track ALL past failed attempts so the model never repeats the same mistake
if "attempt_history" not in st.session_state:
    st.session_state.attempt_history = []


# ---------- Helpers ----------
@st.cache_data(ttl=600)
def get_past_lessons():
    try:
        response = supabase.table("lessons").select("lesson_text").execute()
        return [row["lesson_text"] for row in response.data]
    except Exception:
        return []

def save_lesson(lesson_text_val):
    try:
        supabase.table("lessons").insert({"lesson_text": lesson_text_val}).execute()
    except Exception:
        pass


def call_ai(prompt):
    """The Ultimate AI Engine: Tries User Key -> 4 Gemini Models -> Groq Llama 3"""
    
    # 1. User Key Failsafe
    if user_gemini_key:
        try:
            temp_client = genai.Client(api_key=user_gemini_key)
            response = temp_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2)
            )
            st.sidebar.caption(f"🤖 Answered by: `gemini-2.5-flash` (via your personal key)")
            output_parts = [part.text for candidate in response.candidates for part in candidate.content.parts if part.text]
            return "\n".join(output_parts) if output_parts else response.text
        except Exception as e:
            raise Exception(f"🛑 Your personal API key failed: {e}")

    # 2. Default Gemini Fallback Chain
    last_error = None
    for model_id in GEMINI_MODELS:
        config = types.GenerateContentConfig(temperature=0.2)

        try:
            response = default_ai_client.models.generate_content(model=model_id, contents=prompt, config=config)
            output_parts = [part.text for candidate in response.candidates for part in candidate.content.parts if part.text]
            st.sidebar.caption(f"🤖 Answered by: `{model_id}`")
            return "\n".join(output_parts) if output_parts else response.text

        except Exception as e:
            error_str = str(e)
            last_error = e

            if "404" in error_str or "NOT_FOUND" in error_str:
                st.sidebar.caption(f"⚠️ `{model_id}` not found/supported, skipping...")
                continue

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                st.sidebar.caption(f"⚡ `{model_id}` rate-limited, trying next model...")
                continue
            else:
                st.sidebar.caption(f"❌ `{model_id}` failed, trying next model...")
                continue
    
    # 3. Groq (Llama-3) Final Fallback
    if groq_client:
        st.sidebar.caption(f"🔄 Gemini models exhausted. Seamlessly switching to Groq...")
        try:
            system_prompt = "You are an elite senior LeetCode tutor. You MUST provide extremely detailed, hand-holding, beginner-friendly explanations. Use step-by-step examples. Explicitly define EVERY technical term. Your code MUST be perfectly optimal and 100% bug-free on the first try. Take a deep breath and think step-by-step before answering."
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=GROQ_MODEL,
                temperature=0.2,
            )
            st.sidebar.caption(f"🤖 Answered by: `{GROQ_MODEL}` (Groq Backup)")
            return chat_completion.choices[0].message.content
        except Exception as groq_e:
            last_error = groq_e
            
    # 4. Total Failure Failsafe
    raise Exception(
        f"🛑 Extremely High Traffic! Both the primary (Gemini) and backup (Groq) servers are currently maxed out.\n\n"
        f"To continue instantly, please paste your own Gemini API key into the sidebar.\n"
        f"(Debug Info: {str(last_error)[:100]})"
    )


# ---------- UI ----------

# Use a callback to persist the text area value into session_state
def _sync_problem():
    st.session_state.problem_text = st.session_state._problem_widget


st.text_area(
    "Paste your coding problem here:",
    height=200,
    key="_problem_widget",
    value=st.session_state.problem_text,
    on_change=_sync_problem,
)

# Convenience alias
problem_text = st.session_state.problem_text

col1, col2 = st.columns(2)
with col1:
    hint_button = st.button("💡 Get Hints", use_container_width=True)
with col2:
    solve_button = st.button("🔍 Reveal Solution", use_container_width=True, type="primary")

# ---------- App Logic ----------

def check_guardrail(text):
    """Fast guardrail check to ensure input is coding-related before wasting tokens."""
    # Fast regex pre-check for extremely short or obviously non-code input
    if len(text.strip()) < 10 and not re.search(r'[\{\}\(\)\[\];=]', text):
        return False
        
    guardrail_prompt = f"Is the following text a valid coding problem, programming concept, or code snippet? Answer with EXACTLY 'YES' or 'NO'. Text: {text}"
    try:
        if groq_client:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": guardrail_prompt}],
                model=BOUNCER_MODEL,
                temperature=0.0,
            )
            response = chat_completion.choices[0].message.content
        else:
            response = call_ai(guardrail_prompt)
        return "YES" in response.upper()
    except:
        return True # Failsafe open if API crashes

if hint_button and problem_text:
    # 1. Guardrail Check
    with st.spinner("👀 Checking input..."):
        is_valid = check_guardrail(problem_text)
        
    if not is_valid:
        st.warning("That doesn't appear to be a valid coding problem. Please paste a valid programming question, assignment, or code snippet.")
        st.stop()

    # Reset solution state for a new problem
    st.session_state.current_solution = None
    st.session_state.attempt_history = []
    st.session_state.lesson_saved = False

    past_lessons = get_past_lessons()
    lessons_context = ""
    if past_lessons:
        lessons_context = "\n\nCRITICAL PAST LESSONS TO REMEMBER:\n" + "\n".join([f"- {l}" for l in past_lessons])

    with st.spinner("Analyzing problem and generating beginner-friendly hints..."):
        prompt = f"""You are a LeetCode Grandmaster and patient tutor. A student wants hints to solve this problem themselves — DO NOT give the final code.

Use this EXACT structure. Write in **short paragraphs**, plain language, and define every technical term.

---

## 💭 1. What's This Problem Really Asking?

Restate the problem in simpler terms. Point out the key observation that leads to the solution, but don't reveal the full approach.

---

## 🧠 2. Concepts You'll Need *(explain each from scratch)*

List the data structures and techniques relevant to this problem. For each one:
- **What is it?** Simple definition with a real-world analogy
- **Why might it help here?** A hint about how it connects

---

## 🪜 3. Step-by-Step Thinking Path *(no code, no pseudo-code)*

Give 3-5 numbered hints that build toward the solution:

1. A gentle nudge about the first thing they should think about
2. A hint about the key insight or pattern
3. What data structure naturally fits and why
4. How to handle edge cases
5. What to optimize for (time/space)

Each hint should be a **question or thought provoker**, not an instruction. The student should still have to figure out the implementation.

---

## ⚠️ 4. Common Pitfalls

1-2 mistakes beginners often make with this type of problem. Warn them without showing how to avoid it.

{lessons_context}

---

**Remember:** DO NOT write any code. DO NOT give the full algorithm. The student wants to learn by doing.
"""
        try:
            result = call_ai(prompt)
            st.markdown("### 💡 Hints & Strategy")
            st.write(result)
        except Exception as e:
            st.error(f"An error occurred: {e}")

elif solve_button and problem_text:
    # 1. Guardrail Check
    with st.spinner("👀 Checking input..."):
        is_valid = check_guardrail(problem_text)
        
    if not is_valid:
        st.warning("That doesn't appear to be a valid coding problem. Please paste a valid programming question, assignment, or code snippet.")
        st.stop()

    # Reset for a fresh solve
    st.session_state.attempt_history = []

    past_lessons = get_past_lessons()
    lessons_context = ""
    if past_lessons:
        lessons_context = "\n\nCRITICAL PAST LESSONS TO AVOID MISTAKES:\n" + "\n".join([f"- {l}" for l in past_lessons])

    with st.spinner("🤖 Initializing AI solvers..."):
        standard_prompt = f"""You are a LeetCode Grandmaster and an expert Python developer. A student has given up on a coding problem.
        
        MANDATORY SELF-CHECK PROCESS:
        You MUST use a <scratchpad> block at the very beginning of your response to dry-run your algorithm against 3 tricky edge cases.
        
        RULES:
        1. Provide the CORRECT, fully working code solution. 
        2. The code MUST be the most efficient, optimal, and concise way to solve the problem (Pythonic style). Do not overcomplicate it.
        3. Format the response beautifully: use clear headings, short paragraphs, and lots of whitespace.
        4. Explain the code step-by-step using simple language for a beginner.
        5. Explicitly define EVERY technical term you use.
        6. Show your verification: include a brief "Verification" section where you trace through one example to prove it works.{lessons_context}
        
        Problem:
        {problem_text}
        """
        
        try:
            final_prompt = standard_prompt
            
            if groq_client:
                with st.spinner("🧠 Agentic Generator: Groq 70B is solving the problem optimally (0 Gemini quota cost)..."):
                    generator_prompt = f"""You are an elite competitive programmer. Solve this coding problem optimally.
                    
                    Problem:
                    {problem_text}
                    
                    RULES:
                    1. Output ONLY the raw, perfect Python code. No explanations, no text, no pleasantries. Just the code.
                    2. PERFORMANCE DIRECTIVE: Your absolute highest priority is Time and Space Complexity. You MUST identify and implement the mathematically optimal approach (e.g., Two Pointers, Sliding Window, Dynamic Programming, Hash Maps).
                    3. BIG-O TARGET: Aim for O(1) space if possible, and the lowest possible O(N) time complexity. Your solution must be designed to beat 99% of submissions on execution speed.
                    4. CORRECTNESS: Accuracy is still mandatory. Do not sacrifice edge-case handling for speed. The code must be flawless.
                    """
                    chat_completion = groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": generator_prompt}],
                        model=GROQ_MODEL,
                        temperature=0.1,
                    )
                    raw_code = chat_completion.choices[0].message.content.strip()
                    
                final_prompt = f"""You are a world-class computer science tutor — patient, thorough, and passionate about teaching. A student has given up on a problem and needs you to hand-hold them from zero to full understanding.

I have already solved the problem perfectly. Here is the exact Python code:

```python
{raw_code}
```
Problem: {problem_text}

Teach this solution using the EXACT structure below. Write in short paragraphs, plain language, and define every technical term like it's the first time the student has heard it. Avoid long blocks of text — break things up.

## 📌 1. What Are We Solving?
Restate the problem in one plain-English sentence. Then answer:

- **Input:** What are we given? (data type, range, an example value)
- **Output:** What must we return?
- **Constraints:** What do the limits tell us? (e.g., "n ≤ 10⁵ means O(n²) will be too slow")

Keep this section short — 3–4 lines max. Just set the stage.

## 🧱 2. The Core Concepts (Explained From Scratch)
For each data structure, algorithm, or technique used in the solution, explain it before we touch any code.

Structure each concept like this:
- **What is it?** A simple definition with a real-world analogy. (e.g., "A hashmap is like a coat check — you hand in your coat (the key) and get a ticket (the value) to find it instantly later.")
- **Why do we need it here?** Why does THIS problem specifically need THIS concept?
- **Visualize it:** Describe it in words so the student can picture it. (e.g., "Imagine two pointers starting at opposite ends of the array, moving toward each other...")

If there are multiple concepts, order them so each one builds on the last. Keep explanations 3–5 sentences per concept. No more.

## 🪜 3. Building the Solution (No Code Yet)
Walk through the algorithm in plain English. Use numbered steps. Each step is one clear thought.

1. First, we ...
2. Then, for each element, we ...
3. If the condition is met, we ...
4. After the loop, we return ...

At every decision point, pause and explain:
- "Why do it this way and not the other way?"
- "What would break if we skipped this step?"

End this section with a 2–3 line pseudo-code summary so they see the full flow before reading real syntax.

## 🐍 4. The Code
(present the exact code here — no changes)

## 🔬 5. Line-by-Line Breakdown
This is the most important section. Take 1–3 lines at a time and explain:

```python
# the code chunk
```
- **What it does:** One sentence in plain language
- **Syntax:** Why this keyword? What does this function return? What does this operator mean?
- **Variable state:** What does each variable hold AFTER this line runs?
- **Watch out:** What might a beginner misunderstand here?

Repeat this until every single line has been covered.

## ✅ 6. Trace Through an Example
Pick the simplest meaningful input. Walk through the code step-by-step using a table:

| Step | Code | Variable State | Why It Happens |
|---|---|---|---|
| 1 | `x = 5` | x = 5 | We set x to the first element |
| 2 | `if x > 0:` | x = 5, condition = True | 5 is greater than 0, so we enter the block |
| ... | ... | ... | ... |

Show the full journey from input → output so the student can visualize exactly how data flows.

## 📊 7. Complexity in Simple Terms
- **Time Complexity:** Why is it O(...)? In plain English: "If the input size doubles, the runtime grows by roughly..."
- **Space Complexity:** Where does the extra memory come from? Does the function use extra arrays, recursion, or does it modify in-place?

## 💡 8. Key Takeaway
One sentence the student should remember for similar problems. (e.g., "When you need to compare elements from both ends of an array, think two pointers.")

{lessons_context}
"""
            
            # Use the fallback chain to process whichever prompt we settled on
            if groq_client:
                with st.spinner("🤖 Agentic Tutor: Gemini is creating a beautiful step-by-step lesson..."):
                    final_result = call_ai(final_prompt)
            else:
                with st.spinner("🤖 Agentic Draft: Generating initial solution with Gemini..."):
                    final_result = call_ai(final_prompt)
                
            # Clean out internal thought processes
            final_result = re.sub(r"<scratchpad>.*?</scratchpad>", "", final_result, flags=re.IGNORECASE | re.DOTALL)
            
            st.session_state.current_solution = final_result.strip()
            st.session_state.attempt_history = [{"role": "solution", "content": final_result.strip()}]
            st.session_state.show_update_alert = False
            st.session_state.lesson_saved = False
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred: {e}")

elif (hint_button or solve_button) and not problem_text:
    st.warning("Paste a problem description above to begin")

# ---------- Display Solution + Feedback Loop ----------
if st.session_state.current_solution:

    # 1. User Message Bubble (The Problem)
    with st.chat_message("user", avatar="👤"):
        st.markdown("**You asked:**")
        st.markdown(problem_text)

    # 2. Assistant Message Bubble (The Solution)
    with st.chat_message("assistant", avatar="🤖"):
        if st.session_state.show_update_alert:
            st.success("The solution was updated based on your error report")
            st.session_state.show_update_alert = False
            st.html('<script>window.parent.document.querySelector("section.main").scrollTo({top: 0, behavior: "smooth"});</script>')

        st.markdown("### Solution Breakdown")
        st.write(st.session_state.current_solution)

        attempt_count = len([a for a in st.session_state.attempt_history if a["role"] == "error"])
        if attempt_count > 0:
            st.caption(f"🔄 This solution has been revised {attempt_count} time(s) based on your feedback.")

        st.divider()

        # --- Positive feedback Bouncer (High Friction) ---
        if st.session_state.get("lesson_saved", False):
            st.success("✅ Saved to AI memory! I will remember this trick for future problems.", icon="🧠")
            if st.button("Undo (Remove from Memory)"):
                try:
                    supabase.table("lessons").delete().eq("lesson_text", st.session_state.get("last_saved_lesson_text", "")).execute()
                    get_past_lessons.clear() # Clear cache
                except:
                    pass
                st.session_state.lesson_saved = False
                st.rerun()
        else:
            st.markdown("#### Save this approach to memory")
            proof_text = st.text_area("Paste your actual technical success output here (e.g., 'Accepted', 'Passed 10/10'):", height=68)
            
            if st.button("Verify & Save", use_container_width=True, type="primary"):
                if not proof_text or len(proof_text) < 3:
                    st.error("Please provide actual proof of execution.")
                elif not groq_client:
                    st.error("Groq API key is required to run the Bouncer AI. Please add it to your environment variables.")
                else:
                    with st.spinner("🤖 Bouncer AI is verifying your proof (costs 0 Gemini quota)..."):
                        bouncer_prompt = f"""You are a strict Bouncer AI. A student claims the AI solution worked.
                        Their proof of execution is:
                        "{proof_text}"

                        1. If this proof is just a casual comment or troll (e.g. 'it worked', 'thanks', '123', 'yes'), you MUST output exactly: REJECT
                        2. If it looks like legitimate technical execution output (e.g. 'Accepted', 'Passed', 'Runtime', 'exit code', '0 errors'), then extract a 1-sentence generalized lesson about WHY the approach works well based on the problem and solution below. Wrap it EXACTLY in <LESSON> and </LESSON> tags.

                        Problem:
                        {problem_text}

                        Solution:
                        {st.session_state.current_solution}
                        """
                        try:
                            chat_completion = groq_client.chat.completions.create(
                                messages=[{"role": "user", "content": bouncer_prompt}],
                                model=BOUNCER_MODEL,
                                temperature=0.1,
                            )
                            bouncer_reply = chat_completion.choices[0].message.content.strip()
                            
                            if "REJECT" in bouncer_reply:
                                st.error("🛑 Bouncer AI Rejected: That doesn't look like actual technical execution output. Nice try! 😉")
                            else:
                                lesson_match = re.search(r"<LESSON>(.*?)</LESSON>", bouncer_reply, re.IGNORECASE | re.DOTALL)
                                if lesson_match:
                                    lesson_text = "✅ PROVEN: " + lesson_match.group(1).strip()
                                else:
                                    clean_reply = bouncer_reply.replace("REJECT", "").strip()
                                    lesson_text = "✅ PROVEN: " + (clean_reply if len(clean_reply) > 5 else "Solution approach verified working.")
                                
                                save_lesson(lesson_text)
                                get_past_lessons.clear() # Clear cache
                                st.session_state.last_saved_lesson_text = lesson_text
                                st.session_state.lesson_saved = True
                                st.balloons()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Bouncer AI encountered an error: {e}")

    st.divider()

    # Floating input at the bottom of the screen
    error_text = st.chat_input("Paste your error output to fix the solution")

    if error_text:
        # Record this failed attempt in history
        st.session_state.attempt_history.append({"role": "error", "content": error_text})
        
        # Truncate history to last 6 entries (3 cycles) to prevent token overflow
        st.session_state.attempt_history = st.session_state.attempt_history[-6:]

        # Build a full history of all past attempts so the model NEVER repeats itself
        history_block = ""
        for i, entry in enumerate(st.session_state.attempt_history):
            if entry["role"] == "solution":
                history_block += f"\n--- ATTEMPT {i // 2 + 1} (YOUR PREVIOUS SOLUTION) ---\n{entry['content']}\n"
            elif entry["role"] == "error":
                history_block += f"\n--- STUDENT ERROR REPORT ---\n{entry['content']}\n"

        past_lessons = get_past_lessons()
        lessons_context = ""
        if past_lessons:
            lessons_context = "\n\nPAST LESSONS FROM YOUR MEMORY:\n" + "\n".join([f"- {l}" for l in past_lessons])

        with st.spinner("Analyzing error, fixing solution, and saving lesson to database..."):
            fix_prompt = f"""You are a LeetCode Grandmaster and an expert Python developer. You have been trying to solve a problem for a student, but your previous solutions FAILED.

            THE PROBLEM:
            {problem_text}
            
            FULL HISTORY OF ALL YOUR ATTEMPTS AND THE STUDENT'S ERROR REPORTS:
            {history_block}
            
            CRITICAL DEBUGGING INSTRUCTIONS:
            1. You have ALREADY tried and FAILED with the approaches above. DO NOT repeat any of them.
            2. Carefully analyze EACH error report. Understand the ROOT CAUSE of every failure.
            3. Design a COMPLETELY NEW approach if the previous logic was fundamentally flawed, or make a PRECISE, targeted fix if it was a small bug.
            4. Before outputting your new solution, mentally trace through at least 2 test cases (including an edge case) to verify it works.

            RESPONSE FORMAT (you MUST follow this exactly):

            ## 🔍 What Went Wrong
            Explain what was wrong with the previous solution in simple language.

            ## ✅ Corrected Solution
            Provide the CORRECT, fully working code. Keep it as simple, efficient, and Pythonic as possible.

            ## 📖 Step-by-Step Explanation
            Explain the FULL corrected code step-by-step as if the student is a complete beginner.
            - Use short paragraphs and bullet points.
            - Explicitly define EVERY technical term you use (e.g., if you say 'O(n)' or 'hashmap', explain what that means simply).
            - Do NOT skip steps or assume prior knowledge.

            ## ✔️ Verification
            Trace through at least one example input to prove the code works.

            ## 🧠 Lesson Learned
            A generalized takeaway from this mistake.{lessons_context}
            
            CRITICAL REQUIREMENT:
            At the very end of your response, you MUST include the generalized lesson wrapped in <LESSON> tags. 
            For example:
            <LESSON>When iterating backwards through an array in Python, remember that the stop index in `range()` is exclusive, so use -1 instead of 0.</LESSON>
            """
            try:
                new_text = call_ai(fix_prompt)

                # Extract and save the lesson
                lesson_match = re.search(r"<LESSON>(.*?)</LESSON>", new_text, re.IGNORECASE | re.DOTALL)
                if lesson_match:
                    lesson_text = lesson_match.group(1).strip()
                    save_lesson(lesson_text)
                    get_past_lessons.clear() # Clear cache
                    st.session_state.last_saved_lesson_text = lesson_text
                    st.session_state.lesson_saved = True
                    new_text = re.sub(
                        r"<LESSON>.*?</LESSON>",
                        f"\n\n**🧠 New Lesson Learned & Saved to Memory:**\n{lesson_text}",
                        new_text,
                        flags=re.IGNORECASE | re.DOTALL,
                    )

                # Add this new solution to the history
                st.session_state.attempt_history.append({"role": "solution", "content": new_text})
                st.session_state.current_solution = new_text
                st.session_state.show_update_alert = True
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {e}")
