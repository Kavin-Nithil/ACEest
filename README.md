# 🏋️ ACEest Fitness & Gym — DevOps CI/CD Project

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.3-lightgrey)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)

> **BITS Pilani WILPD — Introduction to DevOps (CSIZG514/SEZG514) — Assignment 1**

A production-grade Flask REST API for gym program and member management, deployed through a Jenkins-driven CI/CD pipeline with Docker, SonarQube, and Kubernetes rollout strategies on **Minikube**.

---

## 📁 Repository Structure

```
aceest-devops/
├── app.py                        # Flask application (API + business logic)
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Multi-stage Docker build
├── Jenkinsfile                   # Jenkins CI/CD + Minikube deployment pipeline
├── sonar-project.properties      # SonarQube scanner configuration
├── k8s/                          # Kubernetes manifests for all rollout strategies
│   ├── rolling/
│   ├── blue-green/
│   ├── canary/
│   ├── shadow/
│   └── ab-testing/
├── scripts/
│   └── k8s/                      # Deploy / verify / promote / rollback helpers
├── .gitignore
├── .github/
│   └── workflows/
│       └── main.yml              # GitHub Actions CI/CD pipeline
├── tests/
│   ├── __init__.py
│   └── test_app.py               # 50+ Pytest unit & integration tests
└── README.md                     # This file
```

---

## 🚀 API Endpoints

| Method | Endpoint            | Description                          |
|--------|---------------------|--------------------------------------|
| GET    | `/`                 | Home page with endpoint reference    |
| GET    | `/health`           | Service health check                 |
| GET    | `/programs`         | List all training programs           |
| GET    | `/programs/<code>`  | Get program details (FL / MG / BG)   |
| POST   | `/bmi`              | Calculate BMI + WHO classification   |
| POST   | `/calories`         | Calculate TDEE (Mifflin-St Jeor)     |
| POST   | `/members`          | Register a new gym member            |
| GET    | `/members/<id>`     | Retrieve member by ID                |

---

## ⚙️ Local Setup & Execution

### Prerequisites
- Python 3.12+
- pip
- Docker (for containerized runs)
- Git

### 1 — Clone the Repository

```bash
git clone https://github.com/<YOUR_USERNAME>/aceest-devops.git
cd aceest-devops
```

### 2 — Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows
```

### 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### 4 — Run the Flask Application

```bash
python app.py
```

The API will be live at **http://localhost:5000**.

Test it:
```bash
curl http://localhost:5000/health
curl http://localhost:5000/programs

# BMI calculation
curl -X POST http://localhost:5000/bmi \
  -H "Content-Type: application/json" \
  -d '{"weight_kg": 72, "height_cm": 175}'

# TDEE calculation
curl -X POST http://localhost:5000/calories \
  -H "Content-Type: application/json" \
  -d '{"weight_kg": 72, "height_cm": 175, "age": 28, "gender": "male", "activity": "moderate"}'

# Add a member
curl -X POST http://localhost:5000/members \
  -H "Content-Type: application/json" \
  -d '{"name": "Arjun Sharma", "age": 28, "program": "MG"}'
```

---

## 🧪 Running Tests Manually

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage Report

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Run a Specific Test Class

```bash
pytest tests/test_app.py::TestBMIRoute -v
```

### Generate HTML Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html          # macOS
xdg-open htmlcov/index.html      # Linux
```

Expected output — **50+ tests, all passing, ≥ 80% coverage**.

---

## 🐳 Docker — Build & Run

### Build the Image

```bash
docker build -t aceest-fitness:latest .
```

### Run the Container

```bash
docker run -d -p 5000:5000 --name aceest aceest-fitness:latest
```

Visit **http://localhost:5000**

### Run Tests Inside the Container

```bash
docker run --rm \
  -v $(pwd)/tests:/app/tests \
  --entrypoint python \
  aceest-fitness:latest \
  -m pytest tests/ -v
```

### Stop & Remove the Container

```bash
docker stop aceest && docker rm aceest
```

### Dockerfile Design Decisions

| Decision | Reason |
|----------|--------|
| **Multi-stage build** | Stage 1 compiles packages; Stage 2 is clean runtime — smaller final image |
| **python:3.12-slim** | Minimal OS footprint vs full Debian image |
| **Non-root user** | Security best practice — container cannot escalate privileges |
| **HEALTHCHECK** | Docker/Kubernetes can detect unhealthy containers automatically |
| **No test files baked in** | Runtime image stays lean; tests are mounted at CI time |

---

## ☸️ Kubernetes Deployment Strategies

The repository now includes Minikube-ready manifests and Jenkins automation for:

- **Rolling Update** using Kubernetes native rollout history and `kubectl rollout undo`
- **Blue-Green Deployment** with `aceest-active` and `aceest-preview` services plus service-selector cutover
- **Canary Release** with NGINX Ingress weighted routing and deterministic header-based verification
- **Shadow Deployment** with mirrored traffic to a non-user-facing candidate service
- **A/B Testing** with header-based routing between variant A and variant B

The Flask `/health` endpoint exposes deployment metadata so each strategy can be validated during the pipeline.

Key folders:

```text
k8s/
  namespace.yaml
  configmap.yaml
  rolling/
  blue-green/
  canary/
  shadow/
  ab-testing/

scripts/k8s/
  deploy_strategy.sh
  verify_rollout.sh
  promote_release.sh
  rollback.sh
```

Minikube prerequisites:

```bash
minikube start
minikube addons enable ingress
```

---

## 🔧 Jenkins — BUILD Configuration

### Prerequisites
Install these Jenkins plugins:
- **Pipeline**
- **Git**
- **Docker Pipeline**
- **HTML Publisher**
- **JUnit**

### Step-by-Step Setup

1. **Start Jenkins** (if running locally via Docker):
   ```bash
   docker run -d -p 8080:8080 -p 50000:50000 \
     -v jenkins_home:/var/jenkins_home \
     -v /var/run/docker.sock:/var/run/docker.sock \
     --name jenkins jenkins/jenkins:lts
   ```

2. **Open Jenkins** → http://localhost:8080 → Unlock using the initial admin password.

3. **Create a new Pipeline job**:
   - Dashboard → **New Item** → Enter name `aceest-pipeline` → Select **Pipeline** → OK

4. **Configure the job**:
   - Under **Pipeline** section → **Definition**: select `Pipeline script from SCM`
   - **SCM**: Git
   - **Repository URL**: `https://github.com/<YOUR_USERNAME>/aceest-devops.git`
   - **Branch**: `*/main`
   - **Script Path**: `Jenkinsfile`
   - Click **Save**

5. **Trigger a build**:
   - Click **Build Now**
   - Watch the **Stage View** for all 6 stages to pass ✅

### Jenkins Pipeline Stages

```
Checkout → Setup Environment → Lint → Test → Docker Build → Container Smoke Test
```

| Stage | Action | Artifact |
|-------|--------|----------|
| Checkout | Pull repository and deployment assets | — |
| Build Container Image | `docker build` | `aceest-fitness:<tag>` |
| Pytest In Container | Execute tests inside the built image | `reports/junit.xml`, `reports/coverage.xml`, `reports/htmlcov/` |
| SonarQube Analysis | Run static analysis and upload reports | SonarQube dashboard + `reports/sonar-report-task.txt` |
| Quality Gate | Stop pipeline on failed quality gate | — |
| Prepare Minikube | Enable ingress and load the image into Minikube | — |
| Deploy Strategy | Apply manifests for the selected rollout mode | Kubernetes resources |
| Verify Deployment | Strategy-specific health validation | — |
| Promote Or Finalize | Blue-green cutover / canary promotion / no-op finalization | — |

---

## ⚡ GitHub Actions — CI/CD Pipeline

### Pipeline Triggers
- Every **`git push`** to any branch
- Every **Pull Request**

### Workflow File
`.github/workflows/main.yml`

### Pipeline Architecture

```
Push / PR
    │
    ▼
┌─────────────────────┐
│   Job 1: lint       │  flake8 syntax + style check
│   (ubuntu-latest)   │
└──────────┬──────────┘
           │ (on success)
           ▼
┌─────────────────────┐
│   Job 2: test       │  pytest + coverage ≥ 80%
│   (ubuntu-latest)   │  uploads coverage.xml artifact
└──────────┬──────────┘
           │ (on success)
           ▼
┌─────────────────────┐
│   Job 3: docker     │  docker build
│   (ubuntu-latest)   │  pytest inside container
│                     │  curl smoke test
│                     │  Trivy vulnerability scan
└─────────────────────┘
```

### Job Descriptions

#### Job 1 — Build & Lint
- Checks out code
- Installs Python 3.12 + dependencies
- Runs `flake8` — **hard fails** on syntax errors (E9, F63, F7, F82)
- Verifies `app.py` imports without errors

#### Job 2 — Automated Testing
- Runs full `pytest` suite with `--cov-fail-under=80`
- Uploads `coverage.xml` as a workflow artifact
- Only runs if Job 1 passes (`needs: lint`)

#### Job 3 — Docker Image Assembly
- Builds multi-stage Docker image tagged with commit SHA
- Mounts `tests/` directory and runs pytest **inside the container**
- Starts the container and hits `/health` + `/programs` with `curl`
- Runs Trivy security scan (informational)
- Only runs if Job 2 passes (`needs: test`)

### Viewing Results
1. Go to your GitHub repository → **Actions** tab
2. Click on the latest workflow run
3. Expand each job to see step-by-step logs
4. Download the `coverage-report` artifact from the run summary

---

## 🔄 Git Workflow & Commit Strategy

```bash
# Feature development
git checkout -b feature/add-bmi-endpoint
# ... make changes ...
git add app.py tests/test_app.py
git commit -m "feat: add POST /bmi endpoint with WHO classification"
git push origin feature/add-bmi-endpoint
# → opens a PR → GitHub Actions pipeline runs automatically

# Merge to main
git checkout main
git merge feature/add-bmi-endpoint
git push origin main
# → pipeline runs again on main
```

### Commit Message Convention (Conventional Commits)

| Prefix | Use case |
|--------|----------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `test:` | Adding or updating tests |
| `ci:` | CI/CD pipeline changes |
| `docs:` | Documentation only |
| `refactor:` | Code restructure, no behavior change |
| `chore:` | Dependency updates, build scripts |

---

## 📊 Architecture Overview

```
Developer Machine
      │
      │  git push
      ▼
  GitHub Repo ─────────────────► GitHub Actions
      │                               │
      │  SCM Poll / Webhook           │  1. Lint (flake8)
      ▼                               │  2. Test (pytest)
   Jenkins                            │  3. Docker Build + Test
      │                               │  4. Smoke Test
      │  6-stage pipeline             │  5. Trivy Scan
      ▼                               ▼
  Docker Image                   Docker Image
  aceest-fitness:<BUILD>         aceest-fitness:<SHA>
```

---

## 🛡️ Quality Gates Summary

| Gate | Tool | Threshold |
|------|------|-----------|
| Syntax errors | flake8 | Zero tolerance |
| Test pass rate | pytest | 100% must pass |
| Code coverage | pytest-cov | ≥ 80% |
| Container health | curl /health | HTTP 200 |
| Security scan | Trivy | Report HIGH/CRITICAL |

---

## 👥 Author

**ACEest DevOps — BITS Pilani WILPD**  
Course: Introduction to DevOps (CSIZG514 / SEZG514 / SEUSZG514)  
Assignment 1 — S2 2025
