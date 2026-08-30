# Insurance Claim Fraud Investigation Assistant

A decision-support prototype that analyzes auto-insurance claims (structured data, accident narratives, and
accident photos) to estimate fraud probability, flag claims for human review, and explain **why** - built as
a college project on a 100-claim curated dataset. See `docs/model_and_system_explanation.md` for how it
works and `docs/limitations.md` for what it doesn't do.

This README is also the user manual: it takes you from a brand-new computer (no Python installed) to a
running app.

---

## 1. Setup from scratch (new computer, nothing installed)

These steps assume you're starting with a plain Windows, Mac, or Linux machine. Skip any step you've
already done.

### 1.1 Install Python

The project needs **Python 3.10 or newer**.

- **Windows:** Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest
  Python 3.x installer. Run it, and on the first installer screen **check the box "Add python.exe to
  PATH"** before clicking Install - this step is easy to miss and without it the `python`/`pip` commands
  below won't work.
- **Mac:** Install [Homebrew](https://brew.sh) if you don't have it, then run `brew install python`.
- **Linux:** Python 3 is usually preinstalled; if not, use your distro's package manager, e.g.
  `sudo apt install python3 python3-pip python3-venv` on Ubuntu/Debian.

Verify it worked by opening a new terminal (PowerShell on Windows, Terminal on Mac/Linux) and running:

```bash
python --version
```

(On Mac/Linux this may need to be `python3 --version` instead.) You should see `Python 3.10.x` or higher.

### 1.2 Install Git (only needed if you're cloning from GitHub rather than downloading a ZIP)

- **Windows:** download and install from [git-scm.com](https://git-scm.com/downloads).
- **Mac:** `brew install git` (or it prompts to install with Xcode command line tools).
- **Linux:** `sudo apt install git`.

### 1.3 Get the project onto the new computer

Either clone it:

```bash
git clone <your-repo-url>
cd Swasti
```

or copy/download the project folder directly and open a terminal inside it.

### 1.4 Create a virtual environment and install dependencies

A virtual environment keeps this project's Python packages separate from everything else on the machine.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

**Mac/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

You'll need to run the "activate" command again every time you open a new terminal to work on this project.

### 1.5 Set your Gemini API key

Get a free key from [Google AI Studio](https://aistudio.google.com/apikey) if you don't have one, then:

```bash
cp .env.example .env      # Mac/Linux
copy .env.example .env    # Windows
```

Open `.env` in any text editor and replace the placeholder with your real key:

```
GEMINI_API_KEY=your-actual-key-here
```

### 1.6 Verify the data layer and train the model (one-time setup)

Run these once, in order, from the project's root folder:

```bash
python -m fraud_detect.data.verify_mapping
python -m fraud_detect.ml.train
python -m evaluation.run_full_evaluation
python -m evaluation.generate_fp_fn_writeups
python -m fraud_detect.cache.build_gemini_cache
```

The first checks the data is wired up correctly (should print `verify_mapping: PASSED`). The second trains
and saves the ML model (`models/model.joblib`). The third and fourth regenerate the evaluation report shown
in the app's Evaluation Dashboard. The fifth precomputes Gemini analysis for the 100 historical claims (it
makes ~126 API calls with a 1-second pause between each, so it takes several minutes - you only need to run
it once, or again if you add new historical claims).

### 1.7 Run the app

```bash
streamlit run app/streamlit_app.py
```

This opens the app in your browser at `http://localhost:8501`. Use the sidebar to navigate between **New
Claim**, **Browse Existing Claims**, and **Evaluation Dashboard**.

---

## 2. Using the app

### New Claim

Fill in the structured form (vehicle, policyholder, policy, incident, evidence/history fields), optionally
paste adjuster notes and/or upload an accident photo, then click **Analyze Claim**. You'll get:

- a final status (`LEGITIMATE` / `MONITOR` / `ESCALATE` / `HIGH_FRAUD_RISK`), fraud probability, risk score,
  and confidence;
- the top reasons for the decision, a risk-score breakdown, supporting evidence, and any detected
  contradictions between the narrative and structured fields;
- Gemini's photo damage assessment, if a photo was uploaded;
- concrete next steps for a senior investigator, and a downloadable WHY-report.

If you don't provide a narrative or photo, the system still runs the rule engine and ML model on the
structured fields alone - it just skips the Gemini-dependent sections.

### Browse Existing Claims

Explore the 100 historical claims used to build the system, with their real accident narratives and photos
(where available). Gemini analysis for these is precomputed (step 1.6 above), so browsing never makes a
live API call. Ground truth (`FraudFound_P`/`curation_category`) is shown only *after* the prediction, in a
collapsed section, to make clear it isn't used by the scoring engine.

### Evaluation Dashboard

Model performance metrics (accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix), escalation
performance, per-claim predictions, and a false-positive/false-negative writeup - all read from the
precomputed report in `evaluation/evaluation_report/` (regenerate with the commands in step 1.6).

---

## 3. Running the tests

```bash
python -m pytest tests/ -v
```

Covers the data mapping, leakage guard, rule-engine scoring, escalation logic, and end-to-end pipeline
smoke tests (with Gemini calls disabled, so no API key is needed to run them).

---

## 4. Deploying the live demo (Streamlit Community Cloud)

1. Push this repository to GitHub (create a repo, then `git remote add origin <url>` and `git push`).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, and click "New app".
3. Point it at your repo, branch, and `app/streamlit_app.py` as the main file.
4. In the app's **Settings &rarr; Secrets**, paste:
   ```
   GEMINI_API_KEY = "your-actual-key-here"
   ```
5. Deploy. The committed `models/`, `data/processed/`, and `evaluation/evaluation_report/` artifacts mean
   the app works immediately - no training or cache-building needs to happen on the server.

---

## 5. Project structure

```
src/fraud_detect/    Core library: data loading, feature engineering, rule engine, ML model, Gemini layer,
                     decision fusion, WHY-report assembly, and the single pipeline.py orchestration entrypoint.
app/                 Streamlit UI (3 pages: New Claim, Browse Existing Claims, Evaluation Dashboard).
evaluation/          Batch evaluation scripts and their generated report (metrics, confusion matrix,
                     per-claim predictions, false positive/negative analysis).
tests/               Pytest suite.
data/raw/            The original dataset files (untouched).
data/processed/      Generated: claim/report/image mapping, extracted narratives, Gemini cache.
models/              Trained model, preprocessor, model card, tier thresholds.
docs/                This project's other required deliverables (see below).
```

## 6. Other deliverables

- [`docs/model_and_system_explanation.md`](docs/model_and_system_explanation.md) - how the system works, plus an enterprise upgrade path.
- [`docs/limitations.md`](docs/limitations.md)
- [`docs/ai_use_declaration.md`](docs/ai_use_declaration.md)
- [`docs/data_documentation.md`](docs/data_documentation.md)
- [`docs/architecture_diagram.md`](docs/architecture_diagram.md)
- [`docs/test_report/test_report.md`](docs/test_report/test_report.md)
