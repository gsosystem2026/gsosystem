# Push GSO Project to GitHub

Follow these steps to push **only this project** (GSO Final System 2026) to GitHub.

---

## Step 1: Create a new repository on GitHub

1. Go to [github.com](https://github.com) and sign in.
2. Click the **+** (top right) → **New repository**.
3. Choose a name (e.g. `GSO-Final-System-2026`).
4. Choose **Public** (or Private if you have a paid account).
5. **Do not** check "Add a README" or "Add .gitignore" (you already have a project).
6. Click **Create repository**.
7. Copy the repository URL (e.g. `https://github.com/YOUR_USERNAME/GSO-Final-System-2026.git`).

---

## Step 2: Open terminal in this project folder

- Open **PowerShell** or **Command Prompt**.
- Go to the project folder:
  ```powershell
  cd "C:\Users\CLIENT\Desktop\GSO Final System 2026"
  ```

---

## Step 3: Initialize Git here (only this folder)

Run these commands **one at a time**:

```powershell
git init
```

This creates a new Git repo **inside** "GSO Final System 2026" so only this project is tracked (not your whole Desktop).

---

## Step 4: Add and commit your files

```powershell
git add .
git status
```

Check that only project files are listed (no personal folders from Desktop). Then:

```powershell
git commit -m "Initial commit: GSO Request Management System"
```

---

## Step 5: Connect to GitHub and push

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub repo URL:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

**Example:**
```powershell
git remote add origin https://github.com/johndoe/GSO-Final-System-2026.git
git push -u origin main
```

- If GitHub asks for login, use your GitHub username and a **Personal Access Token** (not your password).  
  To create a token: GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Generate new token**.

---

## Later: push updates

After you make more changes:

```powershell
cd "C:\Users\CLIENT\Desktop\GSO Final System 2026"
git add .
git commit -m "Describe what you changed"
git push
```

---

## Note about your Desktop repo

Your **Desktop** folder is currently a Git repo (with GSO_SYSTEM and other folders). The steps above create a **separate** repo only inside "GSO Final System 2026". That way only the GSO project goes to GitHub. You can keep or remove the Desktop repo later; it won’t affect this new one.
