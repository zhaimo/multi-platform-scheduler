# Push to GitHub Instructions

## Step 1: Create Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `multi-platform-scheduler`
3. Description: `Multi-platform video scheduling tool for YouTube, Twitter, and TikTok`
4. Choose: **Public** (so you can use the URL for TikTok application)
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 2: Push Your Code

After creating the repository, run these commands in your terminal:

```bash
cd multi-platform-scheduler

# Add GitHub as remote
git remote add origin https://github.com/zhaimo/multi-platform-scheduler.git

# Push to GitHub
git push -u origin main
```

## Step 3: Verify

Visit: https://github.com/zhaimo/multi-platform-scheduler

You should see all your code!

## Step 4: Use for TikTok Application

When filling out the TikTok developer application, use this URL:
```
https://github.com/zhaimo/multi-platform-scheduler
```

---

## Alternative: If you get authentication errors

If you get authentication errors when pushing, you have two options:

### Option A: Use Personal Access Token (Recommended)
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: "Multi-platform scheduler"
4. Check: `repo` (all repo permissions)
5. Click "Generate token"
6. Copy the token (you won't see it again!)
7. When pushing, use:
   ```bash
   git push -u origin main
   ```
   Username: `zhaimo`
   Password: `<paste your token here>`

### Option B: Use SSH
1. Generate SSH key:
   ```bash
   ssh-keygen -t ed25519 -C "[email]"
   ```
2. Add to GitHub: https://github.com/settings/keys
3. Change remote to SSH:
   ```bash
   git remote set-url origin git@github.com:zhaimo/multi-platform-scheduler.git
   git push -u origin main
   ```

---

## What Gets Pushed

✅ All source code
✅ Documentation
✅ Docker configuration
✅ Setup scripts

❌ .env file (excluded by .gitignore - your secrets are safe!)
❌ node_modules
❌ Python cache files
❌ Database files

---

## After Pushing

Your repository URL will be:
**https://github.com/zhaimo/multi-platform-scheduler**

Use this URL in your TikTok developer application!
