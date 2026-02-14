# Hawaii Fi-Do Dashboard - Quick Start Guide

## 🚀 Deploy in 5 Minutes

### One Command Deployment

```bash
./scripts/deploy-cloudflare-auto.sh
```

**That's it!** The script will:
- ✅ Check all prerequisites
- ✅ Guide you through Cloudflare login (one-time)
- ✅ Build the dashboard
- ✅ Deploy to Cloudflare Pages
- ✅ Walk you through security setup
- ✅ Give you a live URL

### First-Time Setup Walkthrough

**Step 1: Run the deployment script**
```bash
cd /home/user/hawaii-fido-instagram-follower-analysis
./scripts/deploy-cloudflare-auto.sh
```

**Step 2: Provide configuration when prompted**
- Cloudflare project name (default: `hawaii-fido-dashboard`)
- Google Workspace domain (e.g., `hawaiifido.org`)
- Board member emails (optional)

**Step 3: Authenticate with Cloudflare**
- Browser window will open
- Log in with your Cloudflare account (or create free account)
- Grant permissions

**Step 4: Wait for deployment** (~2 minutes)
- Script builds dashboard automatically
- Uploads to Cloudflare Pages
- Provides live URL

**Step 5: Set up Google Workspace SSO** (~5 minutes)
- Script gives you step-by-step instructions
- Configure in Cloudflare dashboard
- One-time setup

**Step 6: Test!**
- Open dashboard URL in incognito mode
- Sign in with Google
- Explore your data!

---

## 📊 Updating Data

When you have new follower data:

```bash
./scripts/update-dashboard.sh
```

This will:
1. Regenerate CSVs from your database
2. Rebuild the dashboard
3. Deploy the update
4. **Time: ~30 seconds**

---

## 🔧 Troubleshooting

**"Wrangler not found"**
```bash
npm install -g wrangler
```

**"Not logged in to Cloudflare"**
```bash
wrangler login
```

**"Build failed"**
```bash
# Check CSV files exist
ls output/*.csv

# Regenerate if needed
python3 scripts/generate_db_reports.py
```

**"Can't access dashboard"**
- Check Cloudflare Access is configured
- Verify your email is in the allow list
- Clear browser cache and try incognito mode

---

## 📖 More Information

- **Full Documentation**: `dashboard/README.md`
- **Configuration Guide**: See "Configuration" section in README
- **Deployment Info**: `dashboard/DEPLOYMENT.md` (created after first deploy)

---

## 🎯 Common Tasks

| Task | Command |
|------|---------|
| **Deploy dashboard** | `./scripts/deploy-cloudflare-auto.sh` |
| **Update data** | `./scripts/update-dashboard.sh` |
| **Build locally** | `python3 dashboard/build/build-dashboard.py` |
| **Test locally** | `xdg-open dashboard/dist/index.html` |
| **View logs** | `wrangler pages deployment tail` |
| **Manage access** | Visit Cloudflare dashboard → Zero Trust |

---

## ⚡ Super Quick Reference

```bash
# First time (5 min)
./scripts/deploy-cloudflare-auto.sh

# Every update (30 sec)
./scripts/update-dashboard.sh

# Test locally
python3 dashboard/build/build-dashboard.py
xdg-open dashboard/dist/index.html
```

**Dashboard URL:** `https://YOUR-PROJECT-NAME.pages.dev`

**Done!** 🎉
