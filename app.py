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

st.set_page_config(page_title="Universal AI Tutor", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Inter:wght@400;500;600&display=swap');
    
    /* Enforce Typography */
    h1, h2, h3, p, li, label {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    
    /* Protect Streamlit Icons */
    span[class*="material-symbols"], i[class*="material-symbols"], .material-icons {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }
    
    /* Deep Rich Code Blocks for IDE Feel */
    code {
        font-family: 'Fira Code', monospace !important;
        color: #38bdf8 !important;
    }
    pre {
        background-color: #020617 !important; /* Pitch slate */
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.8), 0 4px 20px rgba(0,0,0,0.5) !important;
    }
    pre code {
        color: #f8fafc !important;
    }
    
    /* Beautiful Chat Bubbles */
    [data-testid="stChatMessage"] {
        border: 1px solid #334155 !important;
        border-radius: 16px !important;
        padding: 24px !important;
        margin-bottom: 24px !important;
    }
    
    /* Hide Streamlit Default UI Elements */
    #MainMenu {
        visibility: hidden !important;
    }
    header {
        background-color: transparent !important;
    }
    [data-testid="stToolbar"] {
        visibility: hidden !important;
    }
    footer {
        visibility: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Universal AI Coding Tutor")
st.markdown("""
Welcome to your personal AI coding assistant! Paste any coding problem, assignment, or bug below. 
You can choose to get **hints and strategies** to learn and solve it yourself, or click **give up** to see the full solution.
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

import time

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-pro-exp-02-05", "gemini-2.0-flash-lite"]
GROQ_MODEL = "llama-3.3-70b-versatile"
BOUNCER_MODEL = "llama-3.1-8b-instant"

# ---------- UI: Bring Your Own Key ----------
with st.sidebar:
    st.markdown("### 🔑 API Failsafe Settings")
    st.markdown("If the default free API limits are exhausted, you can use your own key here to bypass the limits.")
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
def get_past_lessons():
    try:
        response = supabase.table("lessons").select("lesson").execute()
        return [row["lesson"] for row in response.data]
    except Exception:
        return []


def save_lesson(lesson_text):
    try:
        supabase.table("lessons").insert({"lesson": lesson_text}).execute()
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
                config=types.GenerateContentConfig(temperature=0.2, thinking_config=types.ThinkingConfig(thinking_budget=4096))
            )
            st.sidebar.caption(f"🤖 Answered by: `gemini-2.5-flash` (via your personal key)")
            output_parts = [part.text for candidate in response.candidates for part in candidate.content.parts if part.text and not getattr(part, "thought", False)]
            return "\n".join(output_parts) if output_parts else response.text
        except Exception as e:
            raise Exception(f"🛑 Your personal API key failed: {e}")

    # 2. Default Gemini Fallback Chain
    last_error = None
    for model_id in GEMINI_MODELS:
        supports_thinking = "2.5" in model_id
        config = types.GenerateContentConfig(temperature=0.2)
        if supports_thinking:
            config = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=4096), temperature=0.2)

        try:
            response = default_ai_client.models.generate_content(model=model_id, contents=prompt, config=config)
            output_parts = [part.text for candidate in response.candidates for part in candidate.content.parts if part.text and not getattr(part, "thought", False)]
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
        f"🛑 Extremely High Traffic! Both the primary (Gemini) and backup (Groq) servers are currently maxed out.\\n\\n"
        f"To continue instantly, please paste your own Gemini API key into the sidebar.\\n"
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
    hint_button = st.button("💡 Give Me Hints (No Spoilers!)", use_container_width=True)
with col2:
    solve_button = st.button("✅ Show Full Solution (I Give Up)", use_container_width=True)

# ---------- App Logic ----------
if hint_button and problem_text:
    # Reset solution state for a new problem
    st.session_state.current_solution = None
    st.session_state.attempt_history = []
    st.session_state.lesson_saved = False

    past_lessons = get_past_lessons()
    lessons_context = ""
    if past_lessons:
        lessons_context = "\n\nCRITICAL PAST LESSONS TO REMEMBER:\n" + "\n".join([f"- {l}" for l in past_lessons])

    with st.spinner("Analyzing problem and generating beginner-friendly hints..."):
        prompt = f"""You are a LeetCode Grandmaster and patient tutor. A student needs help with a coding problem.
        
        RULES:
        1. DO NOT give the final code solution.
        2. Explain concepts as if the student is a complete beginner. Avoid assuming prior knowledge.
        3. Explicitly define ANY technical terms you use.
        4. Break down the logic into very small, easily digestible steps.
        5. Use clear visual formatting: lots of spacing, bullet points, and short paragraphs.{lessons_context}
        
        Problem:
        {problem_text}
        """
        try:
            result = call_ai(prompt)
            st.markdown("### 💡 Hints & Strategy")
            st.write(result)
        except Exception as e:
            st.error(f"An error occurred: {e}")

elif solve_button and problem_text:
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
                    
                with st.spinner("🤖 Agentic Tutor: Gemini is creating a beautiful step-by-step lesson..."):
                    final_prompt = f"""You are the world's friendliest, most patient, and most beloved LeetCode Tutor.
                    
                    I have already solved the problem perfectly. Here is the exact, flawless Python code:
                    
                    ```python
                    {raw_code}
                    ```
                    
                    Problem Description:
                    {problem_text}
                    
                    YOUR JOB is to teach this code to a beginner using the following EXACT structure. You MUST act as an explicit, literal pair-programmer.
                    
                    1. **The "Aha!" Moment:** Explain the core logic or trick behind the solution using a simple real-world analogy BEFORE showing any code.
                    2. **The Code Solution:** Present the raw Python code exactly as provided above. DO NOT change a single character of the code logic.
                    3. **Line-by-Line Hand-Holding (CRITICAL):** You MUST break down the code into tiny chunks. Display 1 or 2 lines of the code in a markdown code block, and then explain EXACTLY what those lines do, why that syntax is used, and what the variables are holding under the hood. Repeat this until EVERY SINGLE LINE of the script has been explicitly explained.
                    4. **Example Trace:** Take a simple input example and trace it through the variables step-by-step so the student can visualize the execution.
                    5. **Complexity:** Explain Time and Space complexity in simple terms.{lessons_context}
                    """
            
            # Use the fallback chain to process whichever prompt we settled on
            if not groq_client:
                with st.spinner("🤖 Agentic Draft: Generating initial solution with Gemini..."):
                    pass
                    
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
    st.warning("Please paste a problem description first!")

# ---------- Display Solution + Feedback Loop ----------
if st.session_state.current_solution:

    # 1. User Message Bubble (The Problem)
    with st.chat_message("user", avatar="👤"):
        st.markdown("**You asked:**")
        st.markdown(problem_text)

    # 2. Assistant Message Bubble (The Solution)
    with st.chat_message("assistant", avatar="🤖"):
        if st.session_state.show_update_alert:
            st.success("✨ Success! I analyzed your error report and fixed the solution below!")
            st.balloons()
            st.session_state.show_update_alert = False
            st.html('<script>window.parent.document.querySelector("section.main").scrollTo({top: 0, behavior: "smooth"});</script>')

        st.markdown("### ✅ Full Solution & Explanation")
        st.write(st.session_state.current_solution)

        attempt_count = len([a for a in st.session_state.attempt_history if a["role"] == "error"])
        if attempt_count > 0:
            st.caption(f"🔄 This solution has been revised {attempt_count} time(s) based on your feedback.")

        st.divider()

        # --- Positive feedback Bouncer (High Friction) ---
        if st.session_state.get("lesson_saved", False):
            st.success("✅ Saved to AI memory! I will remember this trick for future problems.", icon="🧠")
            if st.button("Undo (Remove from Memory)"):
                st.session_state.lesson_saved = False
                st.rerun()
        else:
            st.markdown("#### 🏆 Prove it worked to save to memory!")
            proof_text = st.text_area("Paste your actual technical success output here (e.g., 'Accepted', 'Passed 10/10'):", height=68)
            
            if st.button("Verify & Save to Memory", use_container_width=True, type="primary"):
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
                                st.session_state.lesson_saved = True
                                st.balloons()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Bouncer AI encountered an error: {e}")

    st.divider()

    # Floating input at the bottom of the screen
    error_text = st.chat_input("🐛 Did it fail? Paste the specific error or failed test case here to fix the code:")

    if error_text:
        # Record this failed attempt in history
        st.session_state.attempt_history.append({"role": "error", "content": error_text})

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
                st.session_state.lesson_saved = False
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {e}")
