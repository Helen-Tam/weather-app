Project Name: "Flask weather app with GitLab Flow branching strategy"

```text
weather-app/
  ├── static/                    # Static files
  ├── templates/                 # Jinja2 / Flask templates
  ├── app.py                     # Main application code
  ├── Dockerfile                 # Docker image definition
  ├── Jenkinsfile                # CI/CD pipeline
  ├── requirements.txt           # Python dependencies
  └── README.md                  # Project documentation
```

🌿 GitLab Flow on GitHub (Long-lived branches)

🎯 Goal of this model:
- Clear environment separation
- Controlled releases
- Safe hotfixes
- Predictable CI/CD
- Works very well with Jenkins + GitHub + ArgoCD

✅ Long-lived branches (protected)

| Branch       | Meaning                           |
| ------------ | --------------------------------- |
| `develop`    | Integration branch (next release) |
| `main`       | Release-ready / staging           |
| `production` | What is live in prod              |


✅ Short-lived branches

| Branch      | Purpose                    |
| ----------- | -------------------------- |
| `feature/*` | New features               |
| `hotfix/*`  | Emergency production fixes |

🔁 Detailed Flow

1️⃣ Feature development flow:
- Branching
```
git checkout develop
git checkout -b feature/user-auth
```
- Rules:
  - Feature branches always start from develop
  - Never branch from main or production
- Merge (feature/* → develop):
  - Code review
  - Unit tests
  - No deployments yet

2️⃣ Develop → Main (Release preparation):
- When develop is stable: develop → main
- What this means:
  - Feature freeze
  - Release candidate
  - Final QA / security scans

- CI/CD pipeline:

| Branch  | Action                 |
| ------- | ---------------------- |
| develop | Build + tests          |
| main    | Build + staging deploy |


3️⃣ Main → Production (Release):
- Once approved: main → production
- Meaning:
  - This is an explicit release
  - Often requires manual approval
  - Tagged release is created here

- CI/CD pipeline:

| Branch     | Action         |
| ---------- | -------------- |
| production | Deploy to prod |


4️⃣ Hotfix flow:
- Hotfixes start from production, not develop !!!
- Branching:
git checkout production
git checkout -b hotfix/payment-timeout
- Merge sequence:
hotfix → production
hotfix → main
hotfix → develop
- Why?
  - Fix goes live immediately
  - Prevents code divergence
  - Keeps all branches consistent

🔐 Branch protection strategy (conceptual)

| Branch     | Protection       |
| ---------- | ---------------- |
| develop    | PR required      |
| main       | PR + CI required |
| production | PR + approvals   |

🧩 Environment mapping (mental model)

| Branch     | Environment |
| ---------- | ----------- |
| develop    | Dev         |
| main       | Staging     |
| production | Prod        |



✅ ---------------------------- Implementation ---------------------------- ✅

🌿 Creating Branches:
- 1.1 Create develop branch (locally):
```
git checkout main
git pull origin main
git checkout -b develop
git push -u origin develop
```

- 1.2 Create production branch (locally)
```
git checkout main
git checkout -b production
git push -u origin production
```

🔍 Verify branches: git branch -a
- You should see:
```
main
develop
production
remotes/origin/main
remotes/origin/develop
remotes/origin/production
```

🔐 Apply Branch Protection Rules (CRITICAL):
- Go to your repository on GitHub.
- Click Settings → Rules → Add ruleset.

🌿 2.1 Protect production (strictest)
- Ruleset name: production
- Bypass list: Repo admin + dev team
- Branch name pattern: production
- Enable:
  - ✅ Require a PR before merging -> Required approvals (at least 1, preferably 2-3)
  - ✅ Require status checks (can be empty for now)
  - ✅ Require linear commit history 
  - ✅ Restrict deletions
  - ✅ Block force pushes
  
👉 This ensures no direct prod changes

🌿 2.2 Protect main (release-ready):
- Ruleset name: main
- Bypass list: maintainers (release team)
- Branch name pattern: main
- Enable:
  - ✅ Require a PR before merging -> Require approvals (at least 1, preferably 2)
  - ✅ Require status checks (can be empty for now)
  - ✅ Require linear commit history 
  - ✅ Restrict deletions
  - ✅ Block force pushes

👉 main becomes your release gate

🌿 2.3 Protect develop (integration branch)
- Ruleset name: develop
- Bypass list: Repo admin + dev team
- Branch name pattern: develop
- Enable:
  - ✅ Require PR before merging -> Require approvals 0
  - ✅ Restrict deletions
  - ✅ Require linear history 
  - ✅ Block force pushes

👉 Keeps integration clean without slowing dev

🧠 Protection summary:

| Branch     | Purpose           | Protection           |
| ---------- | ----------------- | -------------------- |
| develop    | Integration       | PR required          |
| main       | Release candidate | PR + approvals       |
| production | Live              | PR + strict approval |


