# Deployment Guide

## ✅ Security Check Complete
- `.env` file is properly ignored
- `.data/` directory (databases) is ignored
- No API keys are committed to git
- Initial commit created successfully

## GitHub Repository Setup

### Option 1: Using GitHub Website (Easiest)

1. **Go to GitHub**: https://github.com/new
2. **Repository settings**:
   - Repository name: `annualReportAnalyser` (or your choice)
   - Description: `AI-powered tool for analyzing annual reports and generating asset manager comments`
   - Visibility: **Public** ✅
   - **DO NOT** initialize with README (we already have one)
3. **Click "Create repository"**

4. **Push your code**:
   ```bash
   cd D:\Sweden\annualReportAnalyser
   git remote add origin https://github.com/MadhuAmbat/annualReportAnalyser.git
   git branch -M main
   git push -u origin main
   ```

### Option 2: Install GitHub CLI (Automated)

1. **Install GitHub CLI**:
   ```powershell
   winget install --id GitHub.cli
   ```

2. **Login**:
   ```bash
   gh auth login
   ```

3. **Create and push repo**:
   ```bash
   cd D:\Sweden\annualReportAnalyser
   gh repo create annualReportAnalyser --public --source=. --push
   ```

## 🔒 Environment Variables for Deployment

When deploying, set these environment variables (NOT in git):

```
GEMINI_API_KEY=your_key_here
```

### For Streamlit Cloud:
1. Go to app settings → Secrets
2. Add: `GEMINI_API_KEY = "your_key_here"`

### For Railway/Render:
1. Go to Environment Variables
2. Add: `GEMINI_API_KEY`

## 📦 Deployment Platforms

### Recommended: Railway (Easiest for this app)

1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Add environment variable: `GEMINI_API_KEY`
6. Deploy!

**Cost**: ~$5-10/month

### Alternative: Render (⭐ Auto-detected via render.yaml!)

**Quick Deploy**:
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +" → "Web Service"**
3. **Connect GitHub repository**: `Ambatom4442/annualReportAnalyser`
4. Render will **auto-detect** the `render.yaml` configuration
5. **Add Environment Variable**:
   - Key: `GEMINI_API_KEY`
   - Value: Your Google AI API key
6. Click **"Create Web Service"** - Done! 🎉

**What happens**:
- Installs all dependencies from `requirements.txt`
- Installs Playwright Chromium browser (for JS-rendered URLs)
- Starts Streamlit on port `$PORT` (Render assigns this)
- First deploy takes 5-10 minutes (Playwright install)
- Your app will be live at: `https://annual-report-analyzer-xxxx.onrender.com`

**Manual Configuration** (if auto-detect doesn't work):
- **Build Command**: 
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt && playwright install --with-deps chromium
  ```
- **Start Command**: 
  ```bash
  streamlit run src/app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
  ```

**Cost**: Free tier available (sleeps after 15min inactivity), then $7/month

## 🚨 Before Pushing to GitHub

Run this checklist:

```powershell
cd D:\Sweden\annualReportAnalyser

# 1. Verify .env is ignored
git check-ignore .env
# Should output: .env

# 2. Verify no secrets in staged files
git status
# Should NOT show .env or .data/

# 3. Check commit doesn't contain secrets
git show HEAD | Select-String -Pattern "(API_KEY|SECRET|PASSWORD)" -Context 2
# Should be empty or only show .env.example

# 4. Safe to push!
git push
```

## 📝 Required Files for Deployment

All set! Your repo includes:
- ✅ `.gitignore` (protects secrets)
- ✅ `pyproject.toml` (dependencies)
- ✅ `.env.example` (template for others)
- ✅ `README.md` (documentation)

## 🔄 Updating Your Repo

After making changes:

```bash
git add .
git commit -m "Your commit message"
git push
```

**Never commit**:
- `.env` file
- `.data/` directory
- Any files with API keys
