pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOYMENT_STRATEGY',
            choices: 'rolling\nblue-green\ncanary\nshadow\nab',
            description: 'Deployment strategy to apply in Minikube.'
        )
        string(
            name: 'IMAGE_REPO',
            defaultValue: 'aceest-fitness',
            description: 'Docker image repository/tag prefix available to Minikube.'
        )
        string(
            name: 'IMAGE_TAG',
            defaultValue: '',
            description: 'Optional image tag. Defaults to the Jenkins build number.'
        )
        string(
            name: 'K8S_NAMESPACE',
            defaultValue: 'aceest',
            description: 'Namespace used for Kubernetes resources.'
        )
        string(
            name: 'APP_HOST',
            defaultValue: 'aceest.local',
            description: 'Ingress host used for canary, shadow, and A/B validation.'
        )
        string(
            name: 'CANARY_WEIGHT',
            defaultValue: '20',
            description: 'Percentage of traffic sent to the canary ingress.'
        )
        booleanParam(
            name: 'PROMOTE_CANARY',
            defaultValue: true,
            description: 'Promote the verified canary build into the stable deployment.'
        )
        string(
            name: 'SONARQUBE_SERVER',
            defaultValue: 'SonarQube',
            description: 'Configured Jenkins SonarQube server name.'
        )
        string(
            name: 'SONAR_PROJECT_KEY',
            defaultValue: 'aceest-fitness',
            description: 'SonarQube project key.'
        )
    }

    environment {
        APP_NAME = 'aceest-fitness'
        REPORTS_DIR = 'reports'
        PYTHONUNBUFFERED = '1'
    }

    options {
        timestamps()
        timeout(time: 40, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '15'))
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'chmod +x scripts/k8s/*.sh'
            }
        }

        stage('Initialize') {
            steps {
                script {
                    env.IMAGE_REPO_VALUE = params.IMAGE_REPO
                    env.RESOLVED_IMAGE_TAG = params.IMAGE_TAG?.trim() ? params.IMAGE_TAG.trim() : env.BUILD_NUMBER
                    env.IMAGE = "${params.IMAGE_REPO}:${env.RESOLVED_IMAGE_TAG}"
                }
                sh '''
                    rm -rf ${REPORTS_DIR} .deployment-state
                    mkdir -p ${REPORTS_DIR}/htmlcov
                    echo "Deployment strategy : ${DEPLOYMENT_STRATEGY}"
                    echo "Image               : ${IMAGE}"
                    echo "Namespace           : ${K8S_NAMESPACE}"
                    echo "Ingress host        : ${APP_HOST}"
                '''
            }
        }

        stage('Validate Tooling') {
            steps {
                sh '''
                    # Install Docker CLI if missing
                    if ! command -v docker >/dev/null 2>&1; then
                        apt-get update && apt-get install -y docker.io
                    fi
                    
                    # Install kubectl if missing
                    if ! command -v kubectl >/dev/null 2>&1; then
                        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                        chmod +x kubectl
                        mv kubectl /usr/local/bin/
                    fi
                    
                    # Install minikube if missing
                    if ! command -v minikube >/dev/null 2>&1; then
                        curl -LO "https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64"
                        install minikube-linux-amd64 /usr/local/bin/minikube
                    fi
                    
                    # Install sonar-scanner if missing
                    if ! command -v sonar-scanner >/dev/null 2>&1; then
                        apt-get update && apt-get install -y unzip wget
                        wget -qO sonar-scanner.zip "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip"
                        unzip -q sonar-scanner.zip
                        mv sonar-scanner-5.0.1.3006-linux /opt/sonar-scanner
                        ln -s /opt/sonar-scanner/bin/sonar-scanner /usr/local/bin/sonar-scanner
                        rm sonar-scanner.zip
                    fi

                    command -v docker
                    command -v kubectl
                    command -v minikube
                    command -v sonar-scanner
                    minikube status
                '''
            }
        }

        stage('Build Container Image') {
            steps {
                sh '''
                    docker build \
                      --tag ${IMAGE} \
                      --tag ${IMAGE_REPO_VALUE}:latest \
                      --file Dockerfile \
                      .
                '''
            }
        }

        stage('Pytest In Container') {
            steps {
                sh '''
                    docker run --rm \
                      --user "$(id -u):$(id -g)" \
                      --volume "$PWD:/workspace" \
                      --workdir /workspace \
                      --env PYTHONPATH=/workspace \
                      --entrypoint python \
                      ${IMAGE} \
                      -m pytest tests -v --tb=short \
                      --junitxml=${REPORTS_DIR}/junit.xml \
                      --cov=app \
                      --cov-report=xml:${REPORTS_DIR}/coverage.xml \
                      --cov-report=html:${REPORTS_DIR}/htmlcov \
                      --cov-fail-under=80
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${params.SONARQUBE_SERVER}") {
                    sh '''
                        sonar-scanner \
                          -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
                          -Dsonar.projectVersion=${RESOLVED_IMAGE_TAG} \
                          -Dsonar.buildString=${BUILD_TAG}

                        if [ -f .scannerwork/report-task.txt ]; then
                          cp .scannerwork/report-task.txt ${REPORTS_DIR}/sonar-report-task.txt
                        fi
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Prepare Minikube') {
            steps {
                sh '''
                    minikube addons enable ingress
                    kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=180s
                    minikube image load ${IMAGE}
                '''
            }
        }

        stage('Deploy Strategy') {
            steps {
                withEnv([
                    "DEPLOYMENT_STRATEGY=${params.DEPLOYMENT_STRATEGY}",
                    "IMAGE_REPO=${params.IMAGE_REPO}",
                    "IMAGE_TAG=${env.RESOLVED_IMAGE_TAG}",
                    "K8S_NAMESPACE=${params.K8S_NAMESPACE}",
                    "CANARY_WEIGHT=${params.CANARY_WEIGHT}",
                    "APP_HOST=${params.APP_HOST}"
                ]) {
                    sh 'bash scripts/k8s/deploy_strategy.sh'
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                sh 'bash scripts/k8s/verify_rollout.sh'
            }
        }

        stage('Promote Or Finalize') {
            steps {
                withEnv([
                    "PROMOTE_CANARY=${params.PROMOTE_CANARY}"
                ]) {
                    sh 'bash scripts/k8s/promote_release.sh'
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/junit.xml'
            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports/htmlcov',
                reportFiles: 'index.html',
                reportName: 'Coverage Report'
            ])
            archiveArtifacts artifacts: 'reports/**/*,k8s/**/*.yaml,scripts/k8s/*.sh,sonar-project.properties,.deployment-state',
                             allowEmptyArchive: true
        }
        failure {
            sh 'bash scripts/k8s/rollback.sh || true'
        }
        cleanup {
            cleanWs()
        }
    }
}
