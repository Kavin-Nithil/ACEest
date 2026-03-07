pipeline {

    agent any

    environment {
        IMAGE_NAME    = "aceest-fitness"
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        VENV_DIR      = "venv"
        PYTHONPATH    = "${WORKSPACE}"
    }

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    triggers {
        // Poll GitHub every 5 minutes; replace with webhooks in production
        pollSCM('H/5 * * * *')
    }

    stages {

        // ── Stage 1: Checkout ──────────────────────────────────────────────
        stage('Checkout') {
            steps {
                echo '📥 Pulling latest code from GitHub...'
                checkout scm
                sh 'echo "Branch: ${GIT_BRANCH} | Commit: ${GIT_COMMIT}"'
            }
        }

        // ── Stage 2: Setup Environment ─────────────────────────────────────
        stage('Setup Environment') {
            steps {
                echo '🐍 Setting up Python virtual environment...'
                sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install flake8 pytest-cov
                    echo "✅ Dependencies installed"
                    pip list
                '''
            }
        }

        // ── Stage 3: Lint ──────────────────────────────────────────────────
        stage('Lint') {
            steps {
                echo '🔍 Running flake8 linter...'
                sh '''
                    . ${VENV_DIR}/bin/activate
                    # Hard fail on syntax errors and undefined names
                    flake8 app.py --count --select=E9,F63,F7,F82 \
                        --show-source --statistics
                    # Style checks — informational
                    flake8 app.py --count --exit-zero \
                        --max-complexity=12 --max-line-length=100 \
                        --statistics
                    echo "✅ Lint passed"
                '''
            }
        }

        // ── Stage 4: Unit & Integration Tests ─────────────────────────────
        stage('Test') {
            steps {
                echo '🧪 Running pytest test suite...'
                sh '''
                    . ${VENV_DIR}/bin/activate
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
                    // Publish JUnit results in Jenkins UI
                    junit 'reports/junit.xml'
                    // Publish HTML coverage report
                    publishHTML(target: [
                        allowMissing         : false,
                        alwaysLinkToLastBuild: true,
                        keepAll              : true,
                        reportDir            : 'reports/htmlcov',
                        reportFiles          : 'index.html',
                        reportName           : 'Coverage Report'
                    ])
                }
            }
        }

        // ── Stage 5: Docker Build ──────────────────────────────────────────
        stage('Docker Build') {
            steps {
                echo '🐳 Building Docker image...'
                sh '''
                    docker build \
                        --tag ${IMAGE_NAME}:${IMAGE_TAG} \
                        --tag ${IMAGE_NAME}:latest \
                        --file Dockerfile \
                        .
                    echo "✅ Docker image built: ${IMAGE_NAME}:${IMAGE_TAG}"
                    docker images ${IMAGE_NAME}
                '''
            }
        }

        // ── Stage 6: Smoke Test (container) ───────────────────────────────
        stage('Container Smoke Test') {
            steps {
                echo '💨 Running smoke test inside Docker container...'
                sh '''
                    # Start container
                    docker run -d --name aceest-jenkins-${BUILD_NUMBER} \
                        -p 5001:5000 \
                        ${IMAGE_NAME}:${IMAGE_TAG}
                    sleep 5

                    # Health check
                    curl --fail http://localhost:5001/health && \
                        echo "✅ /health OK" || \
                        (docker logs aceest-jenkins-${BUILD_NUMBER} && exit 1)

                    # Programs endpoint
                    curl --fail http://localhost:5001/programs && \
                        echo "✅ /programs OK" || \
                        (docker logs aceest-jenkins-${BUILD_NUMBER} && exit 1)
                '''
            }
            post {
                always {
                    sh '''
                        docker stop aceest-jenkins-${BUILD_NUMBER} || true
                        docker rm  aceest-jenkins-${BUILD_NUMBER} || true
                    '''
                }
            }
        }

    } // end stages

    post {
        success {
            echo "🎉 BUILD #${env.BUILD_NUMBER} SUCCEEDED — ACEest pipeline complete."
        }
        failure {
            echo "❌ BUILD #${env.BUILD_NUMBER} FAILED — check logs above."
        }
        always {
            // Clean workspace to save disk space
            cleanWs()
        }
    }

}