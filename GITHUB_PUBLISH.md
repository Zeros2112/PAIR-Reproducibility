# Publish this prepared repository to GitHub

The folder is **ready to commit**, but publishing requires your own GitHub authentication. Do not upload the original `PAIR_Project_Results.zip`, the official harmful-behaviors CSV, any `checkpoints/` folder, or generated raw prompt/response files.

## Option A — GitHub Desktop (Windows)

1. Install [GitHub Desktop](https://desktop.github.com/) and sign in.
2. Extract the provided `PAIR_GitHub_Ready.zip` file to a local folder.
3. In GitHub Desktop, choose **File → Add local repository** and select that folder. If GitHub Desktop says it is not a Git repository, select **Create a repository here**.
4. Set the repository name to `PAIR-Reproducibility` (or another name you choose), commit the files, and select **Publish repository**. Choose public/private according to your assignment and safety plan.
5. Confirm the online GitHub repository displays `README.md`, `run_experiment_resumable.py`, `notebooks/`, `results/`, and `tests/`.

## Option B — terminal commands

Create an **empty repository** on GitHub (do not add a second README or `.gitignore` through the website). Then in a terminal opened in the extracted folder:

```bash
git init
git branch -M main
git add .
git status
git commit -m "Add PAIR reproduction, extension, notebook, and results"
git remote add origin https://github.com/YOUR-USERNAME/PAIR-Reproducibility.git
git push -u origin main
```

Replace `YOUR-USERNAME` and the repository name with your own. GitHub will require authentication; use GitHub Desktop or your configured GitHub credential manager, not a password/token embedded in project source.

## After publishing

1. In `notebooks/PAIR_Colab_GitHub.ipynb`, update `GITHUB_USERNAME` and `REPO_NAME` in the first code cell to point at your online repository.
2. Commit and push that small notebook change.
3. Open the notebook in Colab, follow `README.md`, and verify the offline tests and existing result figures regenerate.
4. Copy your final GitHub URL into the **Code** section of the ACL report.
5. Ask a teammate to follow the README from a clean environment. This is especially important because the professor requires an executable README.

**Privacy check:** run `git status` before every commit. `.gitignore` protects generated dataset and checkpoints, but does not protect files that you manually force-added; inspect everything staged under `git diff --cached --stat`.
