pipeline {
    agent any

    environment {
        VENV = '.venv'
        KUBECONFIG = '/var/lib/jenkins/.kube/config'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    rm -rf "$VENV"
                    python3.12 -m venv "$VENV"
                    . "$VENV/bin/activate"
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Syntax Check') {
            steps {
                sh '''
                    . "$VENV/bin/activate"
                    python -m py_compile app.py
                    echo "Syntax Check PASSED"
                '''
            }
        }

        stage('Pytest') {
            steps {
                sh '''
                    . "$VENV/bin/activate"

                    pytest -v \
                        --junitxml=junit.xml \
                        --cov=app \
                        --cov-report=term-missing \
                        --cov-report=xml:coverage.xml
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'SonarScanner'

                    withSonarQubeEnv('SonarQube') {
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                script {
                    timeout(time: 10, unit: 'MINUTES') {

                        def props = readProperties(
                            file: '.scannerwork/report-task.txt'
                        )

                        def ceTaskUrl = props['ceTaskUrl']

                        if (!ceTaskUrl) {
                            error 'Could not find SonarQube CE task URL.'
                        }

                        def analysisId = null

                        while (analysisId == null) {

                            def response = sh(
                                script: "curl -s '${ceTaskUrl}'",
                                returnStdout: true
                            ).trim()

                            def json = readJSON text: response
                            def taskStatus = json.task.status

                            echo "SonarQube task status: ${taskStatus}"

                            if (taskStatus == 'SUCCESS') {

                                analysisId = json.task.analysisId

                            } else if (
                                taskStatus == 'FAILED' ||
                                taskStatus == 'CANCELED'
                            ) {

                                error "SonarQube analysis failed: ${taskStatus}"

                            } else {

                                sleep(
                                    time: 10,
                                    unit: 'SECONDS'
                                )
                            }
                        }

                        def qualityGateResponse = sh(
                            script: """
                                curl -s \
                                'http://localhost:9000/api/qualitygates/project_status?analysisId=${analysisId}'
                            """,
                            returnStdout: true
                        ).trim()

                        def qualityGateJson =
                            readJSON text: qualityGateResponse

                        def qualityGateStatus =
                            qualityGateJson.projectStatus.status

                        echo "Quality Gate Status: ${qualityGateStatus}"

                        if (qualityGateStatus != 'OK') {
                            error "Quality Gate failed: ${qualityGateStatus}"
                        }

                        echo 'QUALITY GATE PASSED'
                    }
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    echo "===== BUILDING DOCKER IMAGE ====="

                    docker build \
                        -t aceest-fitness:build-${BUILD_NUMBER} \
                        .
                '''
            }
        }

        stage('Docker Pytest') {
            steps {
                sh '''
                    echo "===== TESTING INSIDE CONTAINER ====="

                    docker run --rm \
                        aceest-fitness:build-${BUILD_NUMBER} \
                        pytest -v

                    echo "DOCKER PYTEST PASSED"
                '''
            }
        }

        stage('Docker Hub Push') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_TOKEN'
                    )
                ]) {
                    sh '''
                        set +x

                        echo "$DOCKER_TOKEN" |
                        docker login \
                            -u "$DOCKER_USER" \
                            --password-stdin

                        docker tag \
                            aceest-fitness:build-${BUILD_NUMBER} \
                            "$DOCKER_USER/aceest-fitness:build-${BUILD_NUMBER}"

                        docker push \
                            "$DOCKER_USER/aceest-fitness:build-${BUILD_NUMBER}"

                        echo "DOCKER HUB PUSH PASSED"
                    '''
                }
            }
        }

        stage('Kubernetes Pre-Deployment Check') {
            steps {
                sh '''
                    kubectl get nodes

                    kubectl get deployment \
                        aceest-fitness \
                        -n aceest
                '''
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_TOKEN'
                    )
                ]) {
                    script {

                        def deployStatus = sh(
                            returnStatus: true,
                            script: '''
                                kubectl set image \
                                    deployment/aceest-fitness \
                                    aceest-fitness="$DOCKER_USER/aceest-fitness:build-${BUILD_NUMBER}" \
                                    -n aceest

                                kubectl rollout status \
                                    deployment/aceest-fitness \
                                    -n aceest \
                                    --timeout=180s
                            '''
                        )

                        if (deployStatus != 0) {

                            echo 'Deployment failed. Starting rollback.'

                            sh '''
                                kubectl rollout undo \
                                    deployment/aceest-fitness \
                                    -n aceest

                                kubectl rollout status \
                                    deployment/aceest-fitness \
                                    -n aceest \
                                    --timeout=180s
                            '''

                            error(
                                'Deployment failed and rollback was completed.'
                            )
                        }

                        echo 'KUBERNETES DEPLOYMENT PASSED'
                    }
                }
            }
        }

        stage('Kubernetes Health Check') {
            steps {
                script {

                    def healthStatus = sh(
                        returnStatus: true,
                        script: '''
                            kubectl exec \
                                -n aceest \
                                deployment/aceest-fitness \
                                -- python -c "import urllib.request; print(urllib.request.urlopen('http://aceest-service/health', timeout=10).read().decode())"
                        '''
                    )

                    if (healthStatus != 0) {

                        echo 'Health check failed. Starting rollback.'

                        sh '''
                            kubectl rollout undo \
                                deployment/aceest-fitness \
                                -n aceest

                            kubectl rollout status \
                                deployment/aceest-fitness \
                                -n aceest \
                                --timeout=180s
                        '''

                        error(
                            'Health check failed and rollback was completed.'
                        )
                    }

                    echo 'APPLICATION HEALTH CHECK PASSED'
                }
            }
        }

        stage('Deployment Verification') {
            steps {
                sh '''
                    echo "===== DEPLOYED IMAGE ====="

                    kubectl get deployment \
                        aceest-fitness \
                        -n aceest \
                        -o=jsonpath='{.spec.template.spec.containers[0].image}'

                    echo

                    echo "===== RUNNING PODS ====="

                    kubectl get pods \
                        -n aceest \
                        -l app=aceest-fitness

                    echo

                    echo "===== ROLLOUT HISTORY ====="

                    kubectl rollout history \
                        deployment/aceest-fitness \
                        -n aceest
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts(
                artifacts: 'coverage.xml',
                allowEmptyArchive: true
            )

            junit(
                testResults: 'junit.xml',
                allowEmptyResults: true
            )
        }

        success {
            echo 'ACEest CI/CD PIPELINE SUCCESSFUL'
        }

        failure {
            echo 'ACEest CI/CD PIPELINE FAILED'
        }
    }
}
