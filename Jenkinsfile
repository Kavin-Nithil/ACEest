// ─────────────────────────────────────────────────────────────────────────────
// ACEest Fitness & Gym — Jenkinsfile (Declarative Pipeline)
//
// TRIGGER MODEL:
//   This pipeline is designed to be triggered by the GitHub Actions Release
//   job via a webhook/API call. When GitHub publishes a new Release (e.g.
//   v1.0.0), it calls Jenkins' buildWithParameters endpoint, passing:
//
//     RELEASE_TAG   — the git tag that was released  (e.g. "v1.0.0")
//     GITHUB_REPO   — the GitHub repo               (e.g. "user/aceest-devops")
//     RELEASE_URL   — the GitHub Release page URL
//     TRIGGERED_BY  — always "github-release-action"
//
//   Jenkins then checks out EXACTLY that tag and runs a clean BUILD pipeline
//   on the released code — guaranteeing the build is reproducible.
//
// CAN ALSO BE TRIGGERED MANUALLY:
//   Dashboard → aceest-pipeline → Build with Parameters
//   Set RELEASE_TAG to any tag (e.g. v1.0.0) or leave blank for latest main.
//
// REQUIRED JENKINS SETUP:
//   1. Plugins: Pipeline, Git, Docker Pipeline, HTML Publisher, JUnit
//   2. Credentials: Add GitHub repo credentials as ID "github-credentials"
//      (needed only for private repos; skip for public)
//   3. Jenkins must have Docker installed on the agent node
//   4. For GitHub webhook: install "Generic Webhook Trigger" plugin and
//      configure as shown in JENKINS_SETUP.md
//
// PIPELINE STAGES:
//   1. Checkout Release Tag   — git checkout the exact released tag
//   2. Setup Environment      — virtualenv + pip install
//   3. Lint                   — flake8 syntax + style
//   4. Test                   — pytest + JUnit + HTML coverage report
//   5. Docker Build           — build image tagged with release version
//   6. Container Smoke Test   — live curl tests against running container
//   7. Release Confirmation   — print build summary
// ─────────────────────────────────────────────────────────────────────────────

pipeline {

    agent any

    // ── Build parameters — populated by GitHub Actions webhook ──────────────
    parameters {
        string(
            name: 'RELEASE_TAG',
            defaultValue: '',
            description: 'Git tag to build (e.g. v1.0.0). Leave blank to build HEAD of main.'
        )
        string(
            name: 'GITHUB_REPO',
            defaultValue: '',
            description: 'GitHub repository (e.g. username/aceest-devops). Auto-set by webhook.'
        )
        string(
            name: 'RELEASE_URL',
            defaultValue: '',
            description: 'GitHub Release URL. Auto-set by webhook.'
        )
        string(
            name: 'TRIGGERED_BY',
            defaultValue: 'manual',
            description: 'Who triggered this build. Auto-set by webhook.'
        )
    }

    environment {
        // Use the release tag as Docker image tag; fall back to build number
        IMAGE_NAME    = "aceest-fitness"
        IMAGE_TAG     = "${params.RELEASE_TAG ?: env.BUILD_NUMBER}"
        VENV_DIR      = "venv"
        PYTHONPATH    = "${WORKSPACE}"

        // GitHub repo URL — constructed from the parameter
        // Replace <YOUR_USERNAME> with your actual GitHub username here,
        // OR configure it as a Jenkins environment variable.
        GITHUB_REPO_URL = "https://github.com/${params.GITHUB_REPO ?: 'YOUR_USERNAME/aceest-devops'}.git"
    }

    options {
        timestamps()
        timeout(time: 25, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15'))
        // Prevent concurrent builds of the same job
        disableConcurrentBuilds()
    }

    // ── Triggers ─────────────────────────────────────────────────────────────
    // Primary trigger: GitHub Actions calls the REST API (see main.yml Job 4).
    // Secondary trigger: poll SCM every 5 min as a fallback.
    triggers {
        pollSCM('H/5 * * * *')
    }

    stages {

        // ── Stage 1: Checkout the exact released tag ─────────────────────────
        stage('Checkout Release Tag') {
            steps {
                script {
                    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    echo "📥  ACEest Jenkins BUILD Pipeline"
                    echo "    Triggered by : ${params.TRIGGERED_BY}"
                    echo "    Release tag  : ${params.RELEASE_TAG ?: '(none — using main)'}"
                    echo "    GitHub repo  : ${env.GITHUB_REPO_URL}"
                    if (params.RELEASE_URL) {
                        echo "    Release URL  : ${params.RELEASE_URL}"
                    }
                    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                }

                // If a release tag was passed, checkout that exact tag.
                // Otherwise fall back to whatever SCM branch/commit is configured.
                script {
                    if (params.RELEASE_TAG) {
                        checkout([
                            $class: 'GitSCM',
                            branches: [[name: "refs/tags/${params.RELEASE_TAG}"]],
                            userRemoteConfigs: [[
                                url: env.GITHUB_REPO_URL,
                                // credentialsId: 'github-credentials'  // uncomment for private repos
                            ]],
                            extensions: [
                                [$class: 'CleanBeforeCheckout'],      // clean workspace before checkout
                                [$class: 'CloneOption', depth: 0, noTags: false, shallow: false]
                            ]
                        ])
                        echo "✅ Checked out tag: ${params.RELEASE_TAG}"
                    } else {
                        echo "ℹ️  No RELEASE_TAG parameter — using SCM default (main branch)"
                        checkout scm
                    }
                }

                sh '''
                    echo "---"
                    echo "Git commit : $(git rev-parse HEAD)"
                    echo "Git tag    : $(git describe --tags --exact-match 2>/dev/null || echo 'no tag at HEAD')"
                    echo "Branch     : $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'detached HEAD')"
                    echo "---"
                '''
            }
        }

        // ── Stage 2: Setup Python Environment ────────────────────────────────
        // Handles Debian/Ubuntu Jenkins agents where python3-venv and pip
        // are NOT pre-installed (common with the jenkins/jenkins:lts image).
        // Root access is available inside the Jenkins Docker container.
        stage('Setup Environment') {
            steps {
                echo '🐍 Setting up Python environment...'
                sh '''
                    # ── Step 1: Show Python version ────────────────────────────
                    echo "Python path    : $(which python3)"
                    echo "Python version : $(python3 --version)"

                    # ── Step 2: Install python3-venv + pip via apt if missing ──
                    # On Debian/Ubuntu the venv module ships as a SEPARATE apt
                    # package (python3.x-venv) and is not bundled with python3.
                    # The Jenkins LTS Docker image is Debian-based — this check
                    # runs fast (no-op) when the package is already present.
                    if ! python3 -c "import venv" 2>/dev/null; then
                        echo "venv module missing — installing via apt..."
                        apt-get update -qq
                        apt-get install -y \
                            python3-venv \
                            python3-pip \
                            --no-install-recommends -qq
                        echo "✅ python3-venv and python3-pip installed"
                    else
                        echo "✅ venv module already available — skipping apt"
                    fi

                    # ── Step 3: Remove any stale venv from previous builds ─────
                    rm -rf ${VENV_DIR}

                    # ── Step 4: Create a fresh virtual environment ─────────────
                    python3 -m venv ${VENV_DIR}
                    echo "✅ Virtual environment created: ${VENV_DIR}/"

                    # ── Step 5: Activate and upgrade pip ───────────────────────
                    . ${VENV_DIR}/bin/activate
                    python3 -m pip install --upgrade pip --quiet
                    echo "pip: $(pip --version)"

                    # ── Step 6: Install all project + dev dependencies ─────────
                    pip install -r requirements.txt
                    pip install flake8 pytest-cov

                    echo ""
                    echo "✅ All dependencies installed successfully"
                    pip list
                '''
            }
        }

        // ── Stage 3: Lint ─────────────────────────────────────────────────────
        stage('Lint') {
            steps {
                echo '🔍 Running flake8 linter...'
                sh '''
                    . ${VENV_DIR}/bin/activate

                    # Hard fail: syntax errors & undefined names
                    flake8 app.py \
                        --count \
                        --select=E9,F63,F7,F82 \
                        --show-source \
                        --statistics

                    # Style checks (informational only — won't break build)
                    flake8 app.py \
                        --count \
                        --exit-zero \
                        --max-complexity=12 \
                        --max-line-length=100 \
                        --statistics

                    echo "✅ Lint passed"
                '''
            }
        }

        // ── Stage 4: Test ─────────────────────────────────────────────────────
        stage('Test') {
            steps {
                echo '🧪 Running pytest suite with coverage...'
                sh '''
                    . ${VENV_DIR}/bin/activate

                    mkdir -p reports

                    pytest tests/ -v \
                        --tb=short \
                        --junitxml=reports/junit.xml \
                        --cov=app \
                        --cov-report=xml:reports/coverage.xml \
                        --cov-report=html:reports/htmlcov \
                        --cov-fail-under=80

                    echo "✅ All tests passed"
                '''
            }
            post {
                always {
                    // Publish test results in Jenkins UI sidebar
                    junit 'reports/junit.xml'

                    // Publish HTML coverage report in Jenkins UI
                    publishHTML(target: [
                        allowMissing         : false,
                        alwaysLinkToLastBuild: true,
                        keepAll              : true,
                        reportDir            : 'reports/htmlcov',
                        reportFiles          : 'index.html',
                        reportName           : 'Coverage Report'
                    ])

                    // Archive coverage XML as a build artifact
                    archiveArtifacts artifacts: 'reports/coverage.xml',
                                     allowEmptyArchive: false
                }
            }
        }

        // ── Stage 5: Docker Build ─────────────────────────────────────────────
        // Tags the image with BOTH the release tag (e.g. v1.0.0) AND 'latest'.
        stage('Docker Build') {
            steps {
                echo '🐳 Building Docker image...'
                sh '''
                    docker build \
                        --tag ${IMAGE_NAME}:${IMAGE_TAG} \
                        --tag ${IMAGE_NAME}:latest \
                        --file Dockerfile \
                        .

                    echo "✅ Docker image built"
                    docker images ${IMAGE_NAME}
                '''
            }
        }

        // ── Stage 6: Container Smoke Test ─────────────────────────────────────
        stage('Container Smoke Test') {
            steps {
                echo '💨 Running live smoke test against containerised app...'
                sh '''
                    CONTAINER_NAME="aceest-jenkins-${BUILD_NUMBER}"

                    # Start the container
                    docker run -d \
                        --name  ${CONTAINER_NAME} \
                        -p 5001:5000 \
                        ${IMAGE_NAME}:${IMAGE_TAG}

                    echo "Container started — waiting 5 seconds for Flask to boot..."
                    sleep 5

                    # /health endpoint
                    echo "--- Testing /health ---"
                    curl --fail --silent --show-error \
                        http://localhost:5001/health \
                        | python3 -m json.tool
                    echo "✅ /health OK"

                    # /programs endpoint
                    echo "--- Testing /programs ---"
                    curl --fail --silent --show-error \
                        http://localhost:5001/programs \
                        | python3 -m json.tool
                    echo "✅ /programs OK"

                    # /programs/FL endpoint
                    echo "--- Testing /programs/FL ---"
                    curl --fail --silent --show-error \
                        http://localhost:5001/programs/FL \
                        | python3 -m json.tool
                    echo "✅ /programs/FL OK"

                    # POST /bmi endpoint
                    echo "--- Testing POST /bmi ---"
                    curl --fail --silent --show-error \
                        -X POST http://localhost:5001/bmi \
                        -H "Content-Type: application/json" \
                        -d "{\"weight_kg\": 70, \"height_cm\": 175}" \
                        | python3 -m json.tool
                    echo "✅ POST /bmi OK"
                '''
            }
            post {
                always {
                    // Always stop and remove the smoke test container
                    sh '''
                        docker stop aceest-jenkins-${BUILD_NUMBER} || true
                        docker rm   aceest-jenkins-${BUILD_NUMBER} || true
                    '''
                }
            }
        }

        // ── Stage 7: Release Confirmation ────────────────────────────────────
        // Prints a final summary. If a RELEASE_TAG was given, also tags the
        // Docker image with that exact version string.
        stage('Release Confirmation') {
            steps {
                script {
                    sh '''
                        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        echo "🎉  BUILD #${BUILD_NUMBER} COMPLETE"
                        echo ""
                        echo "    Release tag  : ${IMAGE_TAG}"
                        echo "    Docker image : ${IMAGE_NAME}:${IMAGE_TAG}"
                        echo "    Docker image : ${IMAGE_NAME}:latest"
                    '''

                    if (params.RELEASE_URL) {
                        sh "echo '    GitHub Release: ${params.RELEASE_URL}'"
                    }

                    sh '''
                        echo ""
                        echo "    Test results  → Jenkins sidebar: Test Results"
                        echo "    Coverage      → Jenkins sidebar: Coverage Report"
                        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    '''
                }
            }
        }

    } // end stages

    // ── Post-pipeline actions ─────────────────────────────────────────────────
    post {
        success {
            echo "✅ ACEest BUILD #${env.BUILD_NUMBER} (${env.IMAGE_TAG}) — ALL STAGES PASSED"
        }
        failure {
            echo "❌ ACEest BUILD #${env.BUILD_NUMBER} FAILED — review the stage that went red above"
        }
        always {
            // Clean workspace after every build to save disk space
            cleanWs()
        }
    }

} // end pipeline