# Fix: "src refspec master does not match any" Error

## Problem
You tried to push to `master` but your local branch is `main`.

## Solution

### Option 1: Push to `main` (Recommended)

Your branch is `main`, so push to `main`:

```bash
cd /home/srprabhala/Documents/Learning/chat-app-entitlements
git push -u origin main
```

### Option 2: Rename Branch to `master` (if you prefer)

If you want to use `master` instead:

```bash
cd /home/srprabhala/Documents/Learning/chat-app-entitlements
git branch -M master
git push -u origin master
```

---

## Authentication Issue

If you get authentication errors, you have two options:

### Option A: Use Personal Access Token (HTTPS)

1. **Create Personal Access Token:**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Name: "chat-app-entitlements"
   - Select scope: `repo` (full control)
   - Click "Generate token"
   - **Copy the token** (you won't see it again!)

2. **Push with token:**
   ```bash
   git push -u origin main
   # When prompted:
   # Username: srprabhala-learner
   # Password: <paste-your-token-here>
   ```

3. **Save credentials (optional):**
   ```bash
   git config --global credential.helper store
   # Then push again - credentials will be saved
   ```

### Option B: Use SSH (Recommended for frequent use)

1. **Check if you have SSH key:**
   ```bash
   ls -la ~/.ssh/id_*.pub
   ```

2. **If no SSH key, generate one:**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Press Enter to accept defaults
   ```

3. **Add SSH key to GitHub:**
   ```bash
   cat ~/.ssh/id_ed25519.pub
   # Copy the output
   ```
   - Go to: https://github.com/settings/keys
   - Click "New SSH key"
   - Paste the key and save

4. **Change remote to SSH:**
   ```bash
   git remote set-url origin git@github.com:srprabhala-learner/chat-application.git
   ```

5. **Test SSH connection:**
   ```bash
   ssh -T git@github.com
   # Should say: "Hi srprabhala-learner! You've successfully authenticated..."
   ```

6. **Push:**
   ```bash
   git push -u origin main
   ```

---

## Quick Fix Commands

**If using HTTPS with token:**
```bash
cd /home/srprabhala/Documents/Learning/chat-app-entitlements
git push -u origin main
# Enter username: srprabhala-learner
# Enter password: <your-personal-access-token>
```

**If using SSH:**
```bash
cd /home/srprabhala/Documents/Learning/chat-app-entitlements
git remote set-url origin git@github.com:srprabhala-learner/chat-application.git
git push -u origin main
```

---

## Verify After Push

1. Check GitHub: https://github.com/srprabhala-learner/chat-application
2. Verify your code is there
3. Check commit history matches

---

## Current Status

- ✅ Local branch: `main`
- ✅ Remote branch: `origin/main` (exists on GitHub)
- ✅ Commits exist locally
- ⚠️ Need to push to sync

