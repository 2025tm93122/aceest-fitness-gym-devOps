pipeline {
    agent any

    environment {
        VENV = '.venv'
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

                        echo "SonarQube CE Task URL: ${ceTaskUrl}"

                        def analysisId = null

                        while (analysisId == null) {

                            def response = sh(
                                script: "curl -s '${ceTaskUrl}'",
                                returnStdout: true
                            ).trim()

                            if (!response) {
                                error 'Empty response received from SonarQube.'
                            }

                            def json = readJSON text: response
                            def taskStatus = json.task.status

                            echo "SonarQube task status: ${taskStatus}"

                            if (taskStatus == 'SUCCESS') {

                                analysisId = json.task.analysisId

                                echo "SonarQube analysis completed."
                                echo "Analysis ID: ${analysisId}"

                            } else if (
                                taskStatus == 'FAILED' ||
                                taskStatus == 'CANCELED'
                            ) {

                                error "SonarQube analysis failed with status: ${taskStatus}"

                            } else {

                                echo 'Analysis is still processing. Waiting 10 seconds...'

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

                        if (!qualityGateResponse) {
                            error 'Empty Quality Gate response received from SonarQube.'
                        }

                        def qualityGateJson = readJSON(
                            text: qualityGateResponse
                        )

                        def qualityGateStatus =
                            qualityGateJson.projectStatus.status

                        echo "Quality Gate Status: ${qualityGateStatus}"

                        if (qualityGateStatus != 'OK') {
                            error "Quality Gate failed: ${qualityGateStatus}"
                        }

                        echo 'Quality Gate PASSED'
                    }
                }
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
            echo 'ACEest Jenkins pipeline completed successfully.'
        }

        failure {
            echo 'ACEest Jenkins pipeline failed. Check the failed stage and console output.'
        }

        aborted {
            echo 'ACEest Jenkins pipeline was aborted.'
        }
    }
}
