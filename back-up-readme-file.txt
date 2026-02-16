Project Name: "Application deployment + CI/CD with Jenkins and ArgoCD"

```text
weather/
├── app.py                     # Main application code
├── Dockerfile                 # Docker image definition
├── Jenkinsfile                # CI/CD pipeline
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── gitops/                    # GitOps configurations for Argo CD
│   ├── jenkins-agent/         # Helm chart for Jenkins namespace, SA, and RBAC
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── namespace.yaml
│   │       ├── serviceaccount.yaml
│   │       └── rbac.yaml
│   └── weather-app/           # Helm chart for the main application
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── cosign.pub
│       ├── charts/
│       └── templates/
│           ├── _helpers.tpl
│           ├── configmap-key.yaml
│           ├── deployment.yaml
│           ├── job-presync.yaml
│           └── tests/
├── static/                    # Static files
└── templates/                 # Jinja2 / Flask templates
```

✅ Infrastructure components:
1. AWS VPC -> 2 AZs -> 1 public and one private subnet per AZ
2. NAT Gateway for the outbound and inbount traffic for the prinate subnet components
3. ALB for GitLab Server and Jenkins Controller Server
4. ALB for ArgoCD (in the EKS Cluster)
5. ALB for the web-application (in the EKS Cluster)
6. EKS Cluster with 3 namespaces:
  - weather -> namespace for the web-application
  - argocd -> namespace for the ArgoCD 
  - jenkins-agents -> namespace for the Jenkins agent

✅ GitOps directory for the ArgoCD:
1. Helm chart for Jenkins namespace, SA, and RBAC (jenkins-agent/):
  - creates the namespace for the agent to run in
  - creates ServiceAccount with Role and RoleBinding for the Jenkins Controller to deploy the agent pods
2. Helm chart for the main application (weather-app/):
  - has a public key (cosign.pub) for image varification pre-hook
  - configmap-key.yaml -> has the value of the public key and will be mounted to the Job that runs a pre-hook
  - job-presync.yaml -> Job pod configuration for the pre-sync-hook -> validates image digest before deploying it to the weather namespace

✅ Configuration for the Helm Chart in ArgoCD:
1. Create an ArgoCD Project.
2. Configure Source Repository (add the repo URL).
3. Configure Destination Cluster: https://kubernetes.default.svc
4. Configure namespaces: weather, jenkins-agents
5. Optional Settings:
  - Sync Windows / Policies → For production environments
  - Roles / RBAC → Control which users can manage apps in this project
  - Helm / Kustomize Settings → Optional, usually leave defaults
6. Save the Project.

7. Create Apps inside the Project
  - When creating each Argo CD App (like weather-app or jenkins-agent):
  - In the General → Project dropdown, select your new project (weather-project).

Fill in the rest as before:
| App Field             | Value                                                    |
| --------------------- | -------------------------------------------------------- |
| Application Name      | weather-app / jenkins-agent                              |
| Repository URL        | `https://<repo>.git`          |
| Path                  | `gitops/weather-app` / `gitops/jenkins-agent`            |
| Destination Cluster   | `https://kubernetes.default.svc`                         |
| Destination Namespace | `weather` / leave blank (chart creates `jenkins-agents`) |
| Sync Policy           | Automatic / Manual                                       |

8. Benefits of Using a Project
  - Grouping: All apps under weather-project are logically together
  - Security: Apps cannot deploy outside allowed namespaces or repos
  - RBAC: You can assign roles to manage this project only
  - Easier monitoring: Dashboard shows project-level status

✅ Building Jenkins CI pipeline with Pod ephemeral agent:

✅ STEP 1 — Kubernetes Preparation for Jenkins Agents.
1. Update the configuration file for the AWS EKS Cluster access:
- aws eks update-kubeconfig --region eu-north-1 --name my-eks-cluster
2. Verify RBAC Correctness:
- kubectl auth can-i create pods \
  --as system:serviceaccount:jenkins-agents:jenkins-controller \
  -n jenkins-agents
- kubectl auth can-i delete pods \
  --as system:serviceaccount:jenkins-agents:jenkins-controller \
  -n jenkins-agents
- kubectl auth can-i create deployments \
  --as system:serviceaccount:jenkins-agents:jenkins-controller \
  -n jenkins-agents
3. Create ServiceAccount Token AND SAVE IT !!!
- kubectl create token jenkins-controller -n jenkins-agents --duration=6h

✅ STEP 2 — Jenkins Kubernetes Cloud Configuration.
- ⚡ It can talk to the EKS API
- ⚡ It authenticates using the jenkins-controller ServiceAccount
- ⚡ It creates on-demand agent pods in jenkins-agents

1. Install Jenkins Plugin -> Kubernetes

2. Create Kubernetes Credentials in Jenkins:
- ⚡ Add ServiceAccount Token: Manage Jenkins → Credentials → System → Global credentials → Add
   - kind: secret text, 
   - secret: the token generated before, 
   - id: eks-jenkins-sa-token
   
3. Configure Kubernetes Cloud:
- ⚡ Manage Jenkins → Clouds → New Cloud → Kubernetes:
   - Name:	eks
   - Kubernetes URL: EKS API endpoint (kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
   - Kubernetes Namespace:	jenkins-agents
   - Credentials: eks-jenkins-sa-token
   - For not opening 50000 port: enable WebSocket
   
4. Configure Agent Defaults: Pod retention: on failure.

✅ STEP 3 — Security measurements before git push:
1. Secret scanning with pre-commit hook.
- ⚡ Use Git-leaks:
    - Install the framework: pip install pre-commit
    * will create a small script hidden in .git/hooks/pre-commit.
    - Create a config file in root repo: .pre-commit-config.yaml
    * tells that script to download and run Gitleaks.
    - Install the hook: pre-commit install
- ⚡ For quick verification:
  - pre-commit run --all-files
- ⚡ The Result: Every time you run git commit, Gitleaks will scan your staged changes. 
- ⚡ If it finds a secret, it will block the commit and show you where the leak is.

✅ STEP 4 — Jenkinsfile (CI pipeline):
1. Agent Configuration:
- Jenkins dynamically creates a Kubernetes Pod for every pipeline run
- The pod is deleted after the job finishes (ephemeral agent)

Containers inside the Pod:

1️⃣ jnlp container
- Purpose: Jenkins control plane communication
- Handles Jenkins ↔ agent communication
- Runs Git checkout
- Lightweight and stable

2️⃣ main-agent container
- Purpose: Application-level tooling
- Used for: Python, pylint, truffleHog and General scripting

3️⃣ docker container (Docker-in-Docker)
- Purpose: Build and test container images
- Runs Docker daemon
- Builds images
- Runs containers for testing
- Pushes images to Docker Hub

🟢 Stage 1: Clone Repo

🟡 Stage 2: Static Code Analysis (pylint):
- Analyzes app.py for:
- Code style issues
- Bad practices
- Potential bugs
- Extracts numeric score
- Fails build if score < 7.0

🔐 Stage 3: TruffleHog Secret Scan: prevent pushing API keys/tokens accidentally.
- ⚡ Cons for using TruffleHog:
    - You want to detect secrets that don’t follow a known pattern (like random passwords or tokens someone pasted)
    - You want API validation to confirm if the secret is real and active (AWS keys, Slack tokens, etc.)
    - You scan historical commits to find leaked secrets in old commits
    - 👉 TruffleHog is more aggressive and finds more “hidden” things.
   
🛡️ Stage 4: Dependency & Dockerfile Scan:
1. Filesystem scan:
- Scans Python dependencies
- Looks for known CVEs

2. Dockerfile config scan
- Detects: Insecure base images and bad Dockerfile practices

🧪 Stage 5: Build and Test Docker Image:
- Waits for Docker daemon
- Builds the Docker image
- Runs container locally
- Performs HTTP health check
- Cleans up container

🔏 Stage 6: Push and Sign Image:
- ⚡ Prerequisites:
- Install Cosign CLI
- Run the command: cosign generate-key-pair
- This will create 2 files: cosign.key (the private key) and cosign.pub (the public key)
- The public key cosign.pub is stored in public-key directory and stored in GitLab repository.
- The private key cosign.key is uploaded to Jenkins controller credentials:
  - Kind: secret file, 
  - ID: cosign-key, 
  - File: cosign.key (uploaded from the local machine)

- ⚡ Pipeline Stage:
- Logs into Docker Hub
- Pushes image
- Downloads Cosign
- Extracts immutable image digest
- Signs image digest cryptographically
- Cosign automatically pushes the signature artifact to DockerHub (the same registry, under the same repository, in special "cosign-signatures" location).

🔄 Stage 7: Update Image Tag in Helm Chart:
- Updates: gitops/weather-app/values.yaml
- Commits new image tag
- Pushes to Git

📦 Post Actions:
- ⚡ Always: Cleanup
- Removes leftover Docker containers
- Prevents resource leaks on the agent

- ⚡ Success / Failure
- Sends Slack notifications
- Includes: Job name ,Build number ,Direct link. 

🧰 Tool Summary:
| Tool              | Purpose                |
| ----------------- | ---------------------- |
| Jenkins           | CI orchestration       |
| Kubernetes Plugin | Ephemeral build agents |
| Docker            | Build & run images     |
| pylint            | Python code quality    |
| TruffleHog        | Secret detection       |
| Trivy             | Vulnerability scanning |
| Cosign            | Image signing          |
| Git               | GitOps handoff         |
| Argo CD           | Continuous deployment  |
| Slack             | Notifications          |


✅ STEP 5 - Image verification in CD stage (ArgoCD) before deployment.
```text
weather/
├─ gitops/                    # GitOps configurations for Argo CD
   └── weather-app/           # Helm chart for the main application
       ├── Chart.yaml
       ├── values.yaml
       ├── cosign.pub         # Public key for image validation
       ├── charts/
       └── templates/
           ├── configmap-key.yaml    # ConfigMap, has the key value
           ├── deployment.yaml       
           ├── job-presync.yaml      # Pre-Sync Job
           └── tests/
```
- ⚡ Pre-Sync process:
- configmap-key.yaml is uploaded the EKS Cluster
- Job pod starts:
- Runs cosign verification: image signature against the public key
- If verification fails:
    - Job exits non-zero
    - Argo CD marks sync as Failed
    - Deployment never happens
- If verification succeeds:
    - Job completes
    - Argo CD proceeds with deployment
- Job is deleted automatically (clean cluster)


