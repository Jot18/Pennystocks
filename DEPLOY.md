# 🚀 DEPLOY CHEATSHEET

5 steps. Do them in order. Don't skip any.

```
┌──────────────────────────────────────────────────────────┐
│ ① CREATE REPO                                            │
│    github.com/new → name it → ✅ Public → Create         │
│    (don't check "Add README")                            │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ ② UPLOAD FILES                                           │
│    Click "uploading an existing file"                    │
│    Drag the CONTENTS of penny-stock-tracker/             │
│    (NOT the folder itself — drag what's inside it)       │
│    → Commit                                              │
│                                                          │
│    Repo root should show:                                │
│      .github  docs  harvester  .gitignore  README.md     │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ ③ ENABLE WRITE PERMISSIONS                               │
│    Settings → Actions → General                          │
│    Scroll to Workflow permissions                        │
│    ● Read and write permissions → Save                   │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ ④ ENABLE PAGES — THIS IS THE CRITICAL STEP               │
│    Settings → Pages                                      │
│    Source: Deploy from a branch                          │
│    Branch: [main] [/docs]  ← change RIGHT dropdown!      │
│    DO NOT leave it as / (root) — change to /docs         │
│    → Save                                                │
│                                                          │
│    Your URL: https://USERNAME.github.io/REPO-NAME/       │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ ⑤ RUN THE HARVESTER FOR THE FIRST TIME                   │
│    Actions tab → "Hourly Stock Data Harvest"             │
│    → "Run workflow" button → green "Run workflow"        │
│    Wait 2 minutes → refresh dashboard URL                │
│                                                          │
│    Auto-runs hourly Mon-Fri after this.                  │
└──────────────────────────────────────────────────────────┘
```

## ⚠️ If your dashboard URL shows the README

You skipped step ④ or saved the wrong folder.

Settings → Pages → folder dropdown → change to `/docs` → Save → refresh.

## ⚠️ If "loading data..." never resolves

Step ③ wasn't saved (workflow can't write data) OR step ⑤ wasn't done yet (harvester hasn't run).

Check **Actions** tab — should show a green checkmark on the latest run.

## ⚠️ If you uploaded files wrong

Repo top-level should NOT contain a single folder. It should contain:
`.github/` `docs/` `harvester/` `.gitignore` `README.md`

If it shows a single `penny-stock-tracker/` folder containing everything, delete and re-upload **the contents** of that folder, not the folder itself.
