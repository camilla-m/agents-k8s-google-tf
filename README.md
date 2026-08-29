# 🚀 ADK Travel Agents

A simple, scalable AI-powered travel assistant system built with:
- **[Google Agent Development Kit](https://google.github.io/adk-docs/) (`google-adk`)** for the agents themselves - three specialist agents (flight/hotel/activity) plus a coordinator that calls them as tools, served with the framework's own dev UI (`/dev-ui`) and REST API
- **Vertex AI / Gemini** as the underlying model, via GKE Workload Identity (no API keys)
- **Google Kubernetes Engine (GKE)** for container orchestration
- **Terraform** for infrastructure as code

Based on the [camilla-m/agents-k8s-google-tf](https://github.com/camilla-m/agents-k8s-google-tf) repository, simplified for easy deployment and demo purposes.

## 🎯 What This Does

- **Flight Agent**: AI-powered flight search and recommendations
- **Travel Coordinator**: Orchestrates multiple agents for complete trip planning
- **Pure AI Experience**: No database storage, just intelligent agent interactions
- **Cloud-Native**: Scalable on Google Cloud with Kubernetes

## 🛠️ Requirements & Installation

The deployment scripts (`scripts/setup.sh`, `scripts/deploy.sh`) check for four CLI
tools up front and abort with `❌ <tool> is required but not installed` if any is
missing. Install all four before running anything.

| Tool | Minimum version | Used for |
|------|-----------------|----------|
| [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) | 450+ | Enabling APIs, creating the service account, cluster credentials, Artifact Registry auth |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | 1.28+ | Applying the manifests in [k8s/](k8s/), port-forwarding, logs |
| [Terraform](https://developer.hashicorp.com/terraform/install) | 1.0+ (see `required_version` in [terraform/main.tf](terraform/main.tf#L5)) | Provisioning the GKE cluster, node pool and IAM |
| [Docker](https://docs.docker.com/get-docker/) | 24+ | Building and pushing the agent image |

Also required:

- A **Google Cloud project with billing enabled** and the `roles/owner` (or an
  equivalent set of) permissions, since setup enables APIs and creates IAM bindings.
- **Python 3.9+** with `requests`, only if you want to run `scripts/test_adk_demo.py`
  (`pip install requests`). Not needed to deploy.

### Verify what you already have

```bash
gcloud version && kubectl version --client && terraform version && docker --version
```

If every command prints a version, skip to [Quick Start](#-quick-start).

---

### 🐧 Linux (Debian / Ubuntu)

```bash
# Common prerequisites for the apt repositories below
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# 1. Google Cloud SDK (includes gcloud + the gke-gcloud-auth-plugin)
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install -y google-cloud-cli google-cloud-cli-gke-gcloud-auth-plugin

# 2. kubectl (from the same Google repo)
sudo apt-get install -y kubectl

# 3. Terraform (HashiCorp apt repo)
wget -O- https://apt.releases.hashicorp.com/gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install -y terraform

# 4. Docker Engine
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # log out and back in for this to take effect
```

<details>
<summary>Fedora / RHEL / CentOS</summary>

```bash
# Google Cloud SDK + kubectl
sudo tee /etc/yum.repos.d/google-cloud-sdk.repo <<'EOF'
[google-cloud-cli]
name=Google Cloud CLI
baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el9-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF
sudo dnf install -y google-cloud-cli google-cloud-cli-gke-gcloud-auth-plugin kubectl

# Terraform
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
sudo dnf install -y terraform

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```
</details>

<details>
<summary>Arch Linux</summary>

```bash
sudo pacman -S --needed kubectl terraform docker
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
# google-cloud-cli lives in the AUR:
yay -S google-cloud-cli google-cloud-cli-gke-gcloud-auth-plugin
```
</details>

<details>
<summary>Any Linux distro (no root / no package manager)</summary>

```bash
# Google Cloud SDK - installs into ~/google-cloud-sdk and updates your shell rc
curl https://sdk.cloud.google.com | bash && exec -l $SHELL
gcloud components install kubectl gke-gcloud-auth-plugin

# Terraform - static binary
TF_VERSION=1.9.8
curl -fsSLO "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip"
unzip "terraform_${TF_VERSION}_linux_amd64.zip" && mkdir -p ~/.local/bin && mv terraform ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"   # add this line to ~/.bashrc
```
Docker still needs root to install; use [Rootless mode](https://docs.docker.com/engine/security/rootless/) if you cannot use `sudo`.
</details>

---

### 🍎 macOS

Using [Homebrew](https://brew.sh/) (install it first if you don't have it):

```bash
# Homebrew itself
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# All four tools
brew install --cask google-cloud-sdk docker
brew install kubectl terraform

# GKE auth plugin (gcloud needs it to talk to the cluster)
gcloud components install gke-gcloud-auth-plugin
```

Then **launch Docker Desktop once** from Applications so the daemon starts;
`docker --version` works without it, but `docker build` will fail with
`Cannot connect to the Docker daemon` until the daemon is running.

> **Apple Silicon (M1/M2/M3/M4):** the image is built for `linux/amd64` because the
> GKE nodes are x86. `scripts/deploy.sh` already passes `--platform linux/amd64`, so
> there is nothing to configure, but the build runs under emulation and is slower
> than on an Intel Mac.

<details>
<summary>Without Homebrew</summary>

```bash
# Google Cloud SDK (includes gcloud, and can install kubectl)
curl https://sdk.cloud.google.com | bash && exec -l $SHELL
gcloud components install kubectl gke-gcloud-auth-plugin

# Terraform
TF_VERSION=1.9.8
ARCH=$([ "$(uname -m)" = "arm64" ] && echo arm64 || echo amd64)
curl -fsSLO "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_darwin_${ARCH}.zip"
unzip "terraform_${TF_VERSION}_darwin_${ARCH}.zip" && sudo mv terraform /usr/local/bin/
```
Docker Desktop: download the `.dmg` from [docker.com](https://docs.docker.com/desktop/install/mac-install/).
</details>

---

### 🪟 Windows

> **Important:** `scripts/setup.sh`, `deploy.sh`, `cleanup.sh` and `status.sh` are
> **bash** scripts. They will not run in PowerShell or `cmd.exe`. Choose one of the
> two paths below.

#### Option A - WSL2 (recommended)

Gives you a real Linux shell, so the scripts run unmodified.

```powershell
# In PowerShell as Administrator, then reboot
wsl --install -d Ubuntu
```

After rebooting, open the **Ubuntu** terminal and follow the
[Linux (Debian / Ubuntu)](#-linux-debian--ubuntu) steps above. For Docker, install
[Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
and enable **Settings → Resources → WSL Integration → Ubuntu** so the `docker`
command works from inside WSL. Do not install Docker Engine separately inside WSL.

#### Option B - Git Bash + native Windows tools

Install the tools on Windows, then run the scripts from **Git Bash** (bundled with
[Git for Windows](https://git-scm.com/download/win)).

Using [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/)
(ships with Windows 11 and recent Windows 10), in PowerShell:

```powershell
winget install --id Google.CloudSDK       -e
winget install --id Kubernetes.kubectl    -e
winget install --id HashiCorp.Terraform   -e
winget install --id Docker.DockerDesktop  -e
winget install --id Git.Git               -e

# GKE auth plugin
gcloud components install gke-gcloud-auth-plugin
```

Or with [Chocolatey](https://chocolatey.org/install) in an **Administrator**
PowerShell:

```powershell
choco install -y gcloudsdk kubernetes-cli terraform docker-desktop git
gcloud components install gke-gcloud-auth-plugin
```

Close and reopen your terminal afterwards so the updated `PATH` is picked up, then
run the deployment from Git Bash:

```bash
./scripts/setup.sh YOUR_GCP_PROJECT_ID
```

---

### Authenticate with Google Cloud

Do this once, on every platform, before running the deployment:

```bash
gcloud auth login                        # your user account, for the gcloud CLI
gcloud auth application-default login    # ADC, used by the Terraform google provider
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud auth application-default set-quota-project YOUR_GCP_PROJECT_ID
```

`gcloud auth login` and `gcloud auth application-default login` are two different
credential stores. Terraform never reads the first one: the `google` provider only
reads Application Default Credentials (ADC), so **both** commands are required.
Running only `gcloud auth login` makes `terraform plan`/`apply` fail with
`Attempted to load application default credentials ... No credentials loaded`.

Confirm ADC is in place before running Terraform:

```bash
ls ~/.config/gcloud/application_default_credentials.json   # Linux/macOS
# Windows: %APPDATA%\gcloud\application_default_credentials.json
gcloud auth application-default print-access-token >/dev/null && echo "ADC OK"
```

Then confirm the project has billing enabled:

```bash
gcloud beta billing projects describe YOUR_GCP_PROJECT_ID
```

> If `gcloud` is installed but the shell reports `command not found`, the SDK is not
> on your `PATH` yet. Open a new terminal, or source the SDK init file for your shell:
> `source ~/google-cloud-sdk/path.zsh.inc` (zsh) / `source ~/google-cloud-sdk/path.bash.inc` (bash).

## 🚀 Quick Start

Make sure `gcloud`, `kubectl`, `terraform` and `docker` are installed and that you
are authenticated (see [Requirements & Installation](#-requirements--installation)),
then follow these steps to deploy the system automatically:

### 1. Clone the repository and enter the directory
```bash
git clone https://github.com/camilla-m/agents-k8s-google-tf.git
cd agents-k8s-google-tf
```

### 2. Run the automated deployment script
This script initializes Terraform, provisions the GKE cluster, creates the service account, configures Workload Identity bindings, builds the Docker image, and deploys the coordinator application.
```bash
chmod +x ./scripts/setup.sh
./scripts/setup.sh YOUR_GCP_PROJECT_ID
```
*(Note: If the setup encounters any transient API enablement errors, rerun the script to resume)*

### 3. Test the agents
Start port-forwarding to the coordinator service:
```bash
kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel
```

Open the **ADK dev console** in your browser - google-adk's own UI for chatting with
the agents and watching tool calls / sub-agent delegation happen live:
```
http://localhost:8080/dev-ui/
```

Or send a chat request from the terminal instead:
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan a trip to Tokyo"}'
```

There's also a small standalone test page at [ui/index.html](ui/index.html) - open it
directly in a browser (no server needed) and point it at your LoadBalancer IP or
`http://localhost:8080` if you're port-forwarding.

## 🧪 Testing the Agents

### Health Check
```bash
curl http://localhost:8080/health
```

### Flight Agent
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need flights to Tokyo next month"}'
```

### Travel Coordinator
```bash
curl -X POST http://localhost:8080/plan \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Tokyo", 
    "days": 4, 
    "budget": 3000,
    "interests": ["cultural", "food"]
  }'
```

## 🔧 Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │────│ Travel Coordinator │────│  Flight Agent   │
│   (GKE Service) │    │   (Orchestrator)   │    │  (AI Powered)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Google AI       │
                       │ Platform (ADK)  │
                       │ Gemini Pro      │
                       └─────────────────┘
```

## 📊 Key Features

- ✅ **No Database Required** - Pure AI agent interactions
- ✅ **Scalable** - manually via `kubectl scale` (no HorizontalPodAutoscaler is defined yet - add one in k8s/ if you need automatic scaling)
- ✅ **Cloud-Native** - Built for Google Cloud Platform
- ✅ **AI-Powered** - Uses Google's latest AI models
- ✅ **Simple** - Easy to deploy and understand
- ✅ **Production-Ready** - Health checks, monitoring

## 📚 Commands Reference

### Deployment
```bash
./scripts/setup.sh PROJECT_ID  [REGION]        # Quick setup
./scripts/deploy.sh PROJECT_ID [REGION]        # Full deployment
```

### Testing
```bash
pip install requests                           # only dependency of the test script
python3 scripts/test_adk_demo.py               # Automated tests
python3 scripts/test_adk_demo.py --quick       # Quick tests
```

### Cleanup
```bash
./scripts/cleanup.sh PROJECT_ID [REGION]       # Remove all resources
```

## 🔐 Security

- **Workload Identity** for secure GCP service authentication
- **Non-root containers** for enhanced security

## 💰 Cost Optimization

- **Preemptible nodes** in development environment
- **Horizontal Pod Autoscaling** to scale based on demand
- **Efficient resource requests** and limits

## 🚨 Troubleshooting

### `Error: Attempted to load application default credentials ... No credentials loaded`

Full error from `terraform plan` / `terraform apply`:

```
Error: Attempted to load application default credentials since neither `credentials`
nor `access_token` was set in the provider block. No credentials loaded.
To use your gcloud credentials, run 'gcloud auth application-default login'
```

The `google` provider in `terraform/main.tf` sets no `credentials` argument on purpose,
so it falls back to Application Default Credentials. The error means ADC is missing,
expired, or pointing at another project. Fix:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_GCP_PROJECT_ID
gcloud auth application-default print-access-token >/dev/null && echo "ADC OK"
cd terraform && terraform plan
```

Notes:
- `gcloud auth login` alone is **not** enough, it does not write ADC.
- If `gcloud` is not found, source the SDK path file or open a new terminal (see
  [Authenticate with Google Cloud](#authenticate-with-google-cloud)).
- In CI, set `GOOGLE_APPLICATION_CREDENTIALS` to a service account key file instead,
  or use Workload Identity Federation.
- To wipe stale ADC: `gcloud auth application-default revoke`, then log in again.

### Common Issues
```bash
# Authentication issues
gcloud auth login
gcloud auth application-default login

# Cluster access
gcloud container clusters get-credentials adk-travel-cluster --region=us-central1

# Pod issues
kubectl describe pod <pod-name> -n adk-travel
kubectl logs <pod-name> -n adk-travel
```

### `docker push` fails with `connection refused`

```
failed to do request: Head "https://us-central1-docker.pkg.dev/v2/<project>/adk-travel/<image>/blobs/sha256:...":
dial tcp 142.251.107.82:443: connect: connection refused
```

This is a **network** failure on Google's side, not an authentication one (auth problems
return `401` or `denied`, never `connection refused`), and not something wrong with your
machine. `us-central1-docker.pkg.dev` is served by an anycast pool behind
`googlecode.l.googleusercontent.com`, and individual frontends in that pool
intermittently refuse the connection. The same error reproduces from a laptop and from
Cloud Shell, on different IPs each time, and the refusing IPs answer normally again
minutes later.

`scripts/deploy.sh` now retries the push up to 5 times with exponential backoff, which
absorbs this. Blobs that already uploaded are skipped, so retries are cheap. If you are
pushing by hand, just run the command again.

To confirm the pool is healthy before retrying (a `401` is the CORRECT answer here - the
endpoint requires a token):

```bash
for ip in $(dig +short us-central1-docker.pkg.dev A | grep -E '^[0-9]'); do
  printf "%-16s " "$ip"
  curl -sS -o /dev/null -w "%{http_code}\n" --max-time 8 \
    --resolve "us-central1-docker.pkg.dev:443:$ip" \
    https://us-central1-docker.pkg.dev/v2/
done
```

If every IP hangs or is refused for several minutes straight, the block is local rather
than transient: check your VPN, corporate proxy, or the `HTTP_PROXY` / `HTTPS_PROXY`
variables in your shell and in your container runtime's settings. Note that on macOS the
push runs inside your container runtime's VM (Rancher Desktop, Colima, Docker Desktop),
so test from there too:

```bash
docker run --rm alpine:3.20 sh -c \
  'apk add -q curl && curl -sS -o /dev/null -w "%{http_code} %{remote_ip}\n" https://us-central1-docker.pkg.dev/v2/'
```

### `docker push` fails with `denied` / `unauthorized`

The Artifact Registry credential helper is missing from `~/.docker/config.json`.
It should contain:

```json
{
  "credHelpers": {
    "us-central1-docker.pkg.dev": "gcloud"
  }
}
```

`scripts/deploy.sh` registers it automatically, but some tools (Rancher Desktop and
Docker Desktop among them) rewrite `config.json` and drop the entry. Re-add it with:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

### `gcloud: command not found` while the SDK is installed

The installer appends `gcloud` to your shell rc file, so it is missing from
non-interactive shells (scripts, CI, IDE terminals). Prepend it explicitly:

```bash
export PATH="$HOME/google-cloud-sdk/bin:$PATH"   # or the path from `which gcloud`
```

### Useful Debug Commands
```bash
kubectl get events --sort-by='.lastTimestamp' -n adk-travel
kubectl get all -n adk-travel
kubectl top pods -n adk-travel
```

## 📈 Scaling

```bash
# Scale the Travel Coordinator (which runs all agents)
kubectl scale deployment travel-adk-coordinator --replicas=3 -n adk-travel

# Monitor pods
kubectl get pods -n adk-travel
```

## 🎯 Demo Script

Perfect for presentations and demos:

```bash
# 1. Show the deployment
kubectl get all -n adk-travel

# 2. Port forward for demo
kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel &

# 3. Demo the AI agents
curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" \
  -d '{"message": "Plan a 3-day cultural trip to Tokyo with a $2000 budget"}'

# 4. Show real-time logs
kubectl logs -f deployment/travel-adk-coordinator -n adk-travel --tail=10
```

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

**🚀 Ready to deploy AI-powered travel agents on Google Cloud? Start with:**
```bash
chmod +x ./scripts/setup.sh
./scripts/setup.sh your-project-id
```