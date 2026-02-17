 ----------- Project Name: "Flask weather app with GitLab Flow branching strategy" -----------

👉 Repo structure:

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

🌿 Long-lived branches (protected)

| Branch       | Meaning                           |
| ------------ | --------------------------------- |
| `develop`    | Integration branch (next release) |
| `staging`    | Release-ready / staging           |
| `main`       | What is live in prod              |


🌿 Short-lived branches

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

2️⃣ Develop → Staging (Release preparation):
- When develop is stable: develop → staging
- What this means:
  - Feature freeze
  - Release candidate
  - Final QA / security scans

3️⃣ Staging → Main (Release):
- Once approved: staging → main(prod)
- Meaning:
  - This is an explicit release
  - Often requires manual approval
  - Tagged release is created here

4️⃣ Hotfix flow:
- Hotfixes start from main, not develop !!!
- Branching:
git checkout main
git checkout -b hotfix/payment-timeout
- Merge sequence:
hotfix → main
hotfix → staging
hotfix → develop
- Why?
  - Fix goes live immediately
  - Prevents code divergence
  - Keeps all branches consistent



✅ ---------------------------- Implementation ---------------------------- ✅

🌿 Creating Branches:
- 1.1 Create develop branch (locally):
```
git checkout main
git pull origin main
git checkout -b develop
git push -u origin develop
```

- 1.2 Create staging branch (locally)
```
git checkout main
git checkout -b staging
git push -u origin staging
```

🔍 Verify branches: git branch -a
- You should see:
```
main
develop
staging
remotes/origin/main
remotes/origin/develop
remotes/origin/staging
```

🔐 Apply Branch Protection Rules (CRITICAL):
- Go to your repository on GitHub.
- Click Settings → Rules → Add ruleset.

🌿 2.1 Protect main (production)
- Ruleset name: main
- Bypass list: Repo admin
- Branch name pattern: main
- Enable:
  - ✅ Require a PR before merging -> Required approvals (at least 1, preferably 2-3)
  - ✅ Require status checks (can be empty for now)
  - ✅ Require linear commit history 
  - ✅ Restrict deletions
  - ✅ Block force pushes
  
👉 This ensures no direct prod changes

🌿 2.2 Protect staging (release-ready):
- Ruleset name: staging
- Bypass list: maintainers (release team)
- Branch name pattern: staging
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


👉 Stage-to-branch mapping:
| Pipeline Stage                      | develop |   staging   |   main   | Purpose                                   |
| ----------------------------------- | :-----: | :---------: | :------: | ----------------------------------------- |
| Clone App Repo                      |    ✅    |      ✅      |     ✅    | Fetch application source code             |
| Static Code Analysis (pylint)       |    ✅    |      ✅      |     ❌    | Code quality gate before promotion        |
| TruffleHog Secret Scan              |    ✅    |      ✅      |     ✅    | Prevent leaked secrets                    |
| Dependency Scan (Trivy FS + config) |    ✅    |      ✅      |     ✅    | Detect vulnerable dependencies            |
| Build & Test Docker Image           |    ✅    |      ✅      |     ✅    | Build image and run smoke tests           |
| Push Image                          |    ✅    |      ✅      |     ✅    | Publish image used by Helm                |
| Sign Image (Cosign)                 |    ❌    |      ✅      |     ✅    | Supply-chain security for higher envs     |
| Update GitOps Desired State         | ✅ (dev) | ✅ (staging) | ✅ (prod) | Update environment-specific desired state |


🔍 CI/CD Pipeline Stage-by-Stage Explanation
1. Clone App Repo:
- Branches: develop, staging, main
  - Uses Jenkins SCM checkout
  - Provides a clean workspace for analysis and builds

2. Pylint - Static Code Analysis:
- Branches: develop, staging
  - Runs pylint against the Python application to enforce consistent coding standards before promotion
  - Enforces a defined quality score
  - Skipped on main to avoid blocking hotfixes already validated earlier

3. TruffleHog Secret Scan:
- Branches: develop, staging, main
  - Scans repository history and filesystem for leaked secrets
  - Prevents credentials from reaching container images or GitOps repos

4. Dependency Scan (Filesystem & Dockerfile):
- Branches: develop, staging, main
  - Scans project dependencies
  - Scans Dockerfile for insecure patterns
  - Detects vulnerable libraries early
  - Shift-left security

5. Build & Test Docker Image:
- Branches: develop, staging, main
  - Builds the Docker image
  - Runs the container locally
  - Performs a basic HTTP reachability test
  - Ensures the image is runnable
  - Prevents broken images from entering the registry

6. Push Image:
- Branches: develop, staging, main
  - Pushes the image to Docker Hub
  - Image tags are branch-aware: <branch>-<build-number>

7. Sign Image (Conditional) with Cosign:
- Branches: staging, main
  - Signs the image by digest
  - Skipped on develop to keep feedback fast

8. Update GitOps Desired State:
- Branches & Targets:
  - develop → dev
  - staging → staging
  - main → prod
- Clones the GitOps repository
- Updates environment-specific values
- Commits the new desired state



