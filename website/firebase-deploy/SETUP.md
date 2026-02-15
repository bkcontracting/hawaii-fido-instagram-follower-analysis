# Hawaii FIDO Dashboard — Firebase Deployment Guide

## Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Create a project"** (or "Add project")
3. Name it: `hawaii-fido-instagram`
4. Disable Google Analytics (not needed) → Click **Create Project**
5. Wait for it to finish, then click **Continue**

## Step 2: Deploy

Open a terminal, navigate to the `firebase-deploy` folder, then run:

```bash
npx firebase login
npx firebase use hawaii-fido-instagram
npx firebase deploy
```

Your dashboard will be live at:
`https://hawaii-fido-instagram.web.app`

## Password

The dashboard password is: `FiDo2026bd`

Share this with board members along with the URL. The password stays active for the browser session — they won't need to re-enter it until they close the tab.

## Changing the Password

Edit `public/index.html` and find `const DASHBOARD_PW = 'FiDo2026bd';` near the bottom. Change the value and redeploy with `npx firebase deploy`.
