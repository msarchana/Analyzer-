# InsightAI — Intelligent Text Analytics & Context Understanding

A Streamlit student-project upgrade of the original Smart AI Text Analyzer. It retains the existing pretrained models:
- Sentiment: `cardiffnlp/twitter-roberta-base-sentiment-latest`
- Topic classification: `facebook/bart-large-mnli` (zero-shot)

## Features
1. Responsive custom dark UI, branded header, logo-style identity and new project name.
2. Login, registration, password hashing, logout, disabled-account checks.
3. Admin panel, account status management, system usage metrics.
4. Sentiment, topic confidence chart, keyword extraction, text statistics and context notes.
5. CSV batch analysis (up to 100 rows per batch), CSV exports and individual PDF report.
6. Per-user analysis history, search, deletion and export.
7. SQLite persistence for users, analysis records and audit events.
8. Audit logs for sign-in, analysis, account changes and errors; Python operational log at `logs/app.log`.
9. Model/system information page for administrators.

## Requirements
- Windows 10/11
- Python 3.10 or 3.11 recommended
- 8 GB RAM recommended; CPU inference works but may be slow
- Internet connection on first AI model use
- Several GB of free disk space recommended for pretrained model downloads

## Run on Windows using VS Code
1. Extract `InsightAI.zip` into a folder, e.g. `C:\Projects\InsightAI`.
2. Open VS Code → **File → Open Folder** → select the `InsightAI` folder.
3. Open **Terminal → New Terminal**.
4. Check Python:
   ```powershell
   py --version
   ```
5. Create a virtual environment:
   ```powershell
   py -3.11 -m venv .venv
   ```
   If that command fails but Python is installed, try `py -m venv .venv`.
6. Activate it in PowerShell:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt in VS Code and run:
   ```bat
   .venv\Scripts\activate.bat
   ```
7. Install packages:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
   PyTorch/Transformers downloads can take time. If installation fails, note the complete error and Python version.
8. Start the application:
   ```powershell
   python -m streamlit run app.py
   ```
9. Open the local address shown in the terminal, usually `http://localhost:8501`.
10. Create your own account from **Create account**. The first account is a normal user. To create an admin, follow the one-time bootstrap instructions below.

## Create the first administrator (local project setup)
For safer defaults, public registration never creates an admin. Create a user account first. Then close Streamlit and run this one-time command from the project folder:
```powershell
python -c "import database as d; from auth import hash_password; u=d.get_user_by_login('YOUR_USERNAME'); print('User not found' if not u else 'User ID: '+str(u['id']))"
```
Copy the user ID shown. Then run:
```powershell
python -c "import database as d; d.set_user_role(USER_ID, 'admin'); print('Role updated')"
```
Replace `USER_ID` with the numeric ID, e.g. `2`. Restart Streamlit and sign in again. This setup is intended for a local academic demonstration; protect the database file and do not expose the admin bootstrap to public users.

## Important files
- `app.py`: UI, navigation, page logic and actions.
- `auth.py`: password hashing, registration and login.
- `database.py`: SQLite schema, queries, history and audit logs.
- `analyzer.py`: model loading, inference and keyword extraction.
- `reports.py`: PDF report generator.
- `config.py`: project title and model configuration.
- `assets/style.css`: reserved for optional external styles; main theme is embedded in `app.py`.
- `logs/app.log`: operational errors and diagnostic events.
- `insightai.db`: created automatically on first launch.

## Testing checklist
- Create account; verify duplicate username/email is rejected.
- Sign in with correct and incorrect credentials.
- Analyze positive, negative and neutral example text.
- Confirm topic chart, keywords, word/character counts, and PDF download.
- Upload sample CSV and export batch results.
- Confirm history only shows the signed-in user's records.
- Promote a test account to admin; test user management and audit logs.
- Disable a user, then confirm that user cannot continue using the app.
- Delete an analysis and confirm it disappears from history.
- Check `logs/app.log` after intentionally causing an error.

## Limitations / responsible use
- The models are pretrained inference models; this project does not train them from scratch.
- RoBERTa was originally designed for social-media text; results can be wrong for sarcasm, local languages, long documents or domain-specific wording.
- BART topic scores are relative model scores, not calibrated probabilities.
- Keyword extraction is a frequency-based baseline, not a dedicated semantic keyword model.
- SQLite is suitable for a local prototype, not a high-traffic multi-user deployment.
- This is a student prototype. Before public deployment, add HTTPS, CSRF/session hardening appropriate to deployment, rate limiting, secret management, backups, privacy policy and security review.
