How to integrate this repository with GitHub and VS Code (Windows PowerShell)

1) Install Git for Windows

- Download and install from: https://git-scm.com/download/win
- During install, choose "Use Git from the Windows Command Prompt" so `git` is available in PowerShell.
- After install, restart VS Code / PowerShell.

2) Verify git is available

```powershell
git --version
```

3) Create a GitHub repository (two options)

Option A — via the GitHub website (manual):
- Go to https://github.com/new and create a new repo (name e.g. Sokoban_AI)
- Do NOT initialize with README/.gitignore if you already have local files.

Option B — via GitHub CLI (if you have `gh`):
- Install GitHub CLI: https://cli.github.com/
- Run:
```powershell
gh auth login
gh repo create <owner>/<repo> --public --source=. --remote=origin
```

4) Add remote and push from local repo

If you created the repo on the website, GitHub will show commands similar to:
```powershell
git remote add origin https://github.com/<your-user>/<repo>.git
git branch -M main
git push -u origin main
```

5) Sign into GitHub from VS Code

- Open VS Code -> Accounts icon (left bottom) -> Sign in to GitHub
- Follow browser auth flow. After sign-in, VS Code will show GitHub features (PRs, Issues)

6) Use Source Control in VS Code

- Open the Source Control panel (Ctrl+Shift+G)
- Stage, commit and push changes via the UI or use terminal commands.

Troubleshooting notes
- If `git` is not found after install, ensure the installer option to add git to PATH was selected, or add `C:\Program Files\Git\cmd` to PATH.
- If you prefer HTTPS vs SSH for remotes, pick accordingly when adding remote.


Optional: create a GitHub repo and push in one step using the GitHub extension in VS Code
- VS Code command palette (Ctrl+Shift+P) -> "Git: Publish to GitHub" -> follow prompts.
