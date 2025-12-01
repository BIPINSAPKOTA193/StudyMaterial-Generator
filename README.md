# MultiAgent Study Platform

An AI-powered, multi-agent study platform that turns your PDFs and text files into **personalized quizzes, flashcards, and interactive lessons**.  
It tracks your performance over time, learns your preferences with **reinforcement learning**, and persists analytics in the cloud using **Supabase**.

---

## 🎯 What This Project Does

- **Upload study material** (PDF / text) and extract meaningful chunks.
- **Generate three types of content** from your own material:
  - 📝 **Quizzes** – MCQs with explanations and source references  
  - 🃏 **Flashcards** – front/back cards tied to specific chunks  
  - 🎯 **Interactive lessons** – step-by-step guided learning with checkpoints
- **Personalize the experience** using:
  - A short **learning style survey**  
  - A **Thompson Sampling RL agent** that adapts based on your feedback (👍/👎/😐)
- **Track progress** with a rich **Analytics & Progress Dashboard**:
  - Performance by **file** and by **content area**  
  - Strong / weak topics, accuracy, and question counts  
  - Friendly topic names instead of raw chunk IDs
- **Persist everything** (users, RL state, analytics) via **Supabase** so your data survives app restarts and redeployments.

---

## 🏗️ High‑Level Architecture

- **UI Layer – `src/ui/app.py`**
  - Streamlit app handling login, file upload, content display, feedback, and analytics.

- **Core Orchestrator – `src/core/orchestrator.py`**
  - `ManagerAgent` that routes requests between agents and manages session context.

- **Agents – `src/agents/`**
  - `nlp_agent.py`: PDF/text extraction + chunking (with spaCy when available).  
  - `llm_agent.py`: Uses OpenAI (GPT‑4o‑mini by default) to generate quizzes, flashcards, and interactive lessons.  
  - `rl_agent.py`: Thompson Sampling to recommend and adapt learning modes based on user feedback.  
  - `manager_agent.py`: Entry point for UI to talk to the rest of the system.

- **State & Storage – `src/core/`**
  - `memory.py`: RL state + analytics model (`RLState`), with atomic file saves.  
  - `database.py`: Optional local SQLite helpers.  
  - `supabase_client.py`: Reads/writes users and RL/analytics state to Supabase (JSONB).  
  - `analytics.py`: Chunk/file-level performance tracking and user‑friendly naming.

- **Tools – `src/tools/`**
  - `pdf_extractor.py`: Robust PDF/text extraction (pypdf).

---

## 🚀 Running Locally

### 1. Prerequisites

- Python **3.9+**
- `pip` and `virtualenv` (or `venv`)
- An **OpenAI API key**
- Optional: a **Supabase** project for persistent storage

### 2. Setup

```bash
cd QuizGenerator   # or the cloned project directory

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm   # optional but recommended
```

Create a `.env` file (or use Streamlit secrets in the cloud):

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Optional: Supabase (for cloud persistence)
SUPABASE_URL=your-supabase-api-url
SUPABASE_KEY=your-supabase-service-role-or-anon-key
```

### 3. Run the App

```bash
streamlit run src/ui/app.py
```

Open your browser at `http://localhost:8501`.

---

## 📖 How to Use the Platform

1. **Register / Log in**  
   Accounts are stored in Supabase (when configured), or locally as a fallback.

2. **Complete the Learning Style Survey**  
   Choose preferred mode: quiz, flashcards, interactive, or “I don’t know”.

3. **Upload a File**  
   Upload a PDF or text file in the sidebar. The app extracts and chunks the text and registers the file so analytics show **real filenames**, not hashes.

4. **Generate Content**  
   - If you have a strong preference, the app generates that mode.  
   - If you’re unsure, it generates a **mixed bundle** with tabs for quiz / flashcards / interactive.  
   - The number of questions/cards/steps scales with document size.

5. **Interact & Give Feedback**  
   - Answer quiz questions, flip flashcards, follow interactive steps.  
   - Use Like / Dislike / Neutral buttons so the RL agent can adapt future recommendations.

6. **View Analytics**  
   - Open the **Analytics & Progress Dashboard**.  
   - See overall accuracy, performance **by file**, and **by topic/section**, plus strong/weak areas.

---

## 📊 Analytics & Persistence (Supabase)

- **Stored in Supabase**:
  - `users` table – login data.  
  - `rl_state` table – RL + analytics:
    - `chunk_performance` JSONB for per‑chunk stats.  
    - `file_mapping` (hash → filename).  
    - Mode history, survey status, and timestamps.

- **Why**: Streamlit Cloud’s filesystem is ephemeral; Supabase keeps users, analytics, and RL state persistent.

- **Fallback**: If Supabase is not configured, the app uses local JSON/SQLite so it still works offline.

See:
- `SUPABASE_SETUP.md`
- `supabase_setup.sql`
- `SUPABASE_DATA_STORAGE.md`
- `VIEW_ANALYTICS_IN_SUPABASE.md`

---

## 🧠 AI & RL Details (Good for AI Class Demos)

- **LLM Agent (`src/agents/llm_agent.py`)**
  - Uses GPT‑4o‑mini via the OpenAI client.  
  - Strong anti‑hallucination prompts: must use only provided chunks, quote them, and record `"Chunk N - EXACT quote: '...'"`.  
  - Mixed‑bundle generation runs quiz/flashcards/interactive in parallel.

- **Reinforcement Learning Agent (`src/agents/rl_agent.py`)**
  - Thompson Sampling over {quiz, flashcard, interactive}.  
  - Maintains alpha/beta parameters per mode with safeguards to avoid numerical issues.  
  - Caps history length to avoid unbounded memory usage.

- **Adaptive Item Counts (`src/core/orchestrator.py`)**
  - Scales items with chunk count:
    - Quizzes: ~3–20 questions  
    - Flashcards: ~5–25 cards  
    - Interactive: ~2–8 steps  
  - Further adjusts based on how much the user likes previous content.

---

## 📁 Project Structure (Simplified)

```text
src/
  core/
    analytics.py        # analytics, file mapping, topic naming
    auth.py             # user auth (Supabase + local fallback)
    database.py         # optional SQLite helpers
    logger.py           # central logging
    memory.py           # RLState + load/save (Supabase + local)
    orchestrator.py     # ManagerAgent & routing
    messages.py         # request/response dataclasses
    supabase_client.py  # Supabase client helpers

  agents/
    nlp_agent.py        # extraction + chunking
    llm_agent.py        # OpenAI-based content generation
    rl_agent.py         # Thompson Sampling RL
    manager_agent.py    # high-level orchestrator

  tools/
    pdf_extractor.py    # PDF/text extraction

  ui/
    app.py              # Streamlit UI
    theme.css           # styling
```

Additional docs:
- `DEPLOYMENT_GUIDE.md` / `QUICK_DEPLOY.md` – Streamlit Cloud deployment.  
- `PERSISTENT_STORAGE.md` – Why cloud storage is needed.  
- `VIEW_ANALYTICS_IN_SUPABASE.md` – Inspecting analytics in Supabase.

---

## 🐛 Common Issues

- **OpenAI quota errors** (`429`, `insufficient_quota`)  
  Check `https://platform.openai.com/account/billing`, add a payment method, or wait for reset.

- **No analytics after deploy**  
  Configure `SUPABASE_URL` and `SUPABASE_KEY` in Streamlit secrets; ensure `rl_state` table exists.

- **0 chunks extracted**  
  Try a different PDF, export to text, or inspect logs via the “View Logs” expander.

---

## 📜 License & Purpose

This project is intended **for educational and research use**, ideal for:
- Demonstrating **multi‑agent architectures**  
- Showing an end‑to‑end **LLM + RL** personalized learning system  
- Teaching **analytics‑driven adaptive learning**

Built with ❤️ using Python, Streamlit, OpenAI, spaCy, NumPy, and Supabase.
