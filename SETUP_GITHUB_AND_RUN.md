# Setup Guide — GitHub Repository + Running the Ground Station

An in-depth, beginner-friendly walkthrough: from nothing installed to a live
dashboard and a published GitHub repo. Do the parts in order the first time.

**Repository name:** `relocatable-ground-station`
(matches the project title; descriptive and professional; captures the
follows-me-between-hemispheres angle. If you prefer shorter, `ground-station`
also works — just keep it consistent everywhere below.)

---

## Part A — Install the tools (once per machine)

You'll do this on both your Canberra and Ann Arbor machines.

### 1. Python 3
- Download from https://python.org (get 3.11 or newer). On Windows, **tick
  "Add Python to PATH"** during install.
- Verify in a terminal:
  ```bash
  python3 --version
  ```
  (On Windows, `python --version`.)

### 2. Git
- Download from https://git-scm.com. Default options are fine.
- Verify:
  ```bash
  git --version
  ```

### 3. VS Code + Python extension
- Install VS Code from https://code.visualstudio.com.
- Open it, go to the Extensions panel (the four-squares icon), search
  **"Python"** (by Microsoft), and install it.

### 4. A GitHub account
- Sign up at https://github.com if you don't have one. Use a professional-ish
  username — it'll be part of your portfolio URL.

### 5. Tell Git who you are (once)
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```
Use the same email as your GitHub account.

---

## Part B — Connect to GitHub (once per machine)

GitHub no longer accepts your account password from the command line, so set up
one of these. **SSH keys** are the most reliable and only need doing once.

### Option 1 — SSH keys (recommended)
1. Generate a key (press Enter at each prompt to accept defaults):
   ```bash
   ssh-keygen -t ed25519 -C "you@example.com"
   ```
2. Copy the **public** key. Print it and copy the whole line:
   ```bash
   cat ~/.ssh/id_ed25519.pub      # Windows: type %USERPROFILE%\.ssh\id_ed25519.pub
   ```
3. On GitHub: click your avatar → **Settings** → **SSH and GPG keys** →
   **New SSH key** → paste → save.
4. Test:
   ```bash
   ssh -T git@github.com
   ```
   You should see a "successfully authenticated" message.

### Option 2 — GitHub CLI (easiest if you'd rather not touch keys)
Install `gh` from https://cli.github.com, then:
```bash
gh auth login
```
and follow the browser prompts.

---

## Part C — Create the repository and add your files

### 1. Create the empty repo on GitHub
- On GitHub, click **New repository** (the green "New" button).
- **Repository name:** `relocatable-ground-station`
- **Description:** "A portable satellite ground station that predicts passes and
  tracks weather satellites from any location."
- Set it **Public** (it's a portfolio piece — you want it visible).
- **Do NOT** tick "Add a README", ".gitignore", or "license" — you already have
  your own. Leave the repo empty.
- Click **Create repository**.

### 2. Clone it to your computer
Copy the SSH URL from the green **Code** button (looks like
`git@github.com:yourname/relocatable-ground-station.git`), then:
```bash
cd ~/projects                     # or wherever you keep code; make the folder if needed
git clone git@github.com:yourname/relocatable-ground-station.git
cd relocatable-ground-station
```

### 3. Copy the project files in
Move these seven files into the cloned folder:
```
predictor.py   app.py   iss_passes.py   requirements.txt
README.md      LICENSE  .gitignore
```
(`.gitignore` starts with a dot, so it may be hidden in your file browser —
enable "show hidden files" if you don't see it.)

### 4. Put your name in the license
Open `LICENSE` and replace `[Your Name]` with your actual name.

### 5. First commit and push
```bash
git add .
git commit -m "Initial commit: satellite pass predictor (Phases 0-2)"
git push origin main
```
Refresh the GitHub page — your files should appear.

---

## Part D — Run the satellite pass predictor

Do this inside the project folder.

### 1. Create an isolated environment
```bash
python3 -m venv .venv
```
Activate it:
```bash
source .venv/bin/activate         # macOS / Linux
.venv\Scripts\activate            # Windows (PowerShell/CMD)
```
Your prompt should now show `(.venv)`.

> In VS Code, when it asks "We noticed a new virtual environment, do you want to
> select it?", click **Yes**. That makes the ▶ Run button use this environment.

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3a. Run the dashboard (the main event)
```bash
streamlit run app.py
```
Your browser opens automatically (usually http://localhost:8501). In the sidebar:
- pick a **Location** (Canberra or Ann Arbor),
- choose which **Satellites** to track,
- set **Days ahead** and **Min peak elevation** (~25° is a good target).

You'll see: a live world map with current satellite positions, a table of
upcoming passes in local time, and a sky-view plot showing where to point for a
selected pass. Press **Ctrl+C** in the terminal to stop the server.

### 3b. (Optional) Run the minimal CLI
```bash
python3 iss_passes.py
```
Prints the next ISS passes for both stations as plain text — handy for a quick check.

---

## Part E — Troubleshooting

- **"No satellites loaded" / a load warning.** Your machine couldn't reach
  Celestrak. Check your internet, then click **Refresh data** in the sidebar.
  If you're on restrictive Wi-Fi (some campus networks), try another network.
- **"No passes above threshold."** Lower the Min peak elevation slider or raise
  Days ahead. High-latitude, high-elevation passes aren't guaranteed every day.
- **TLE age looks large.** Click Refresh; if it persists, the satellite's data
  may be stale on Celestrak's end — check the NORAD ID is still active.
- **`streamlit: command not found`.** Your venv isn't activated (no `(.venv)` in
  the prompt) — activate it and try again.
- **Port already in use.** Run `streamlit run app.py --server.port 8502`.
- **`git push` rejected / auth failed.** Your SSH key or `gh` login isn't set up
  (see Part B), or you cloned the HTTPS URL instead of SSH.

---

## Part F — Portfolio polish (do once the app runs)

1. **Add a screenshot.** With the dashboard running, take a screenshot, save it
   as `docs/dashboard.png` in the repo (create the `docs/` folder), then:
   ```bash
   git add docs/dashboard.png
   git commit -m "Add dashboard screenshot"
   git push
   ```
   The README already references this path, so it'll appear at the top.
2. **Set the repo "About".** On the GitHub repo page, click the gear next to
   "About" and add the description plus topics:
   `python`, `streamlit`, `skyfield`, `satellite-tracking`, `sdr`, `aerospace`.
3. **Verify constellation status** against https://celestrak.org and note the
   date you checked in the README — turns a caveat into a credibility signal.

---

## Part G — Everyday workflow (as you keep building)

Each time you make changes:
```bash
git add .
git commit -m "Describe what you changed"
git push
```
Check `git status` any time to see what's changed. On your other machine, run
`git pull` before you start work to get the latest, then `git push` when done —
that's how the same repo follows you between Canberra and Ann Arbor.

---

## What you have now

A published, professional repo with a working satellite pass predictor and
dashboard (Phases 0–2). The next phase is the hardware receive leg (RTL-SDR +
SatDump) to capture real weather imagery — everything here is built to schedule
and drive that.
