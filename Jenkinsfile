pipeline {
    agent { label 'bare-metal-agent' }

    environment {
        GITLAB_CREDENTIALS = 'git-lab-key'
        GITLAB_URL = 'ssh://git@git.helen-tam.org:2222/root/weather.git'

        DOCKER_IMAGE_TAG = 'helentam93/weather-app'
        DOCKER_HUB_CREDENTIALS = 'dockerhub-creds'

        TARGET_EC2 = 'ubuntu@51.21.232.104'
        DEPLOY_SSH_CREDENTIALS = 'deploy-server'
    }

    stages {
        stage('Clone Repo') {
            steps {
                echo 'Cloning repository from GitLab...'
                git branch: 'main',
                    credentialsId: "${env.GITLAB_CREDENTIALS}",
                    url: "${env.GITLAB_URL}"
            }
        }

        stage('Pylint Check') {
            steps {
                sh '''
                    echo "Running pylint on app.py..."
                    SCORE=$(pylint app.py | awk '/rated at/ {print $7}' | cut -d'/' -f1)
                    echo "Pylint score: $SCORE"
                    (( $(echo "$SCORE < 5.0" | bc -l) )) && exit 1 || echo "Score OK"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    IMAGE_TAG = "v${currentBuild.startTimeInMillis}"  // Plugin utility can help here too
                    env.IMAGE_TAG = IMAGE_TAG
                    echo "Building Docker image with tag ${IMAGE_TAG}..."
                    docker.build("${DOCKER_IMAGE_TAG}:${IMAGE_TAG}")
                    docker.build("${DOCKER_IMAGE_TAG}:latest")
                }
            }
        }

        stage('Test the app is reachable') {
            steps {
                script {
                    echo "Starting container for testing..."
                    sh '''
                        # remove old test containers if exists
                        docker rm -f weather-test || test
                        docker run -d --name weather-test -p 8000:8000 ${DOCKER_IMAGE_TAG}:${IMAGE_TAG}
                        sleep 10
                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000)
                        echo "HTTP status code: $STATUS"

                        if [ "$STATUS" -ne 200 ]; then
                            echo "App is not reachable. HTTP code: $STATUS"
                            docker logs weather-test
                            docker rm -f weather-test
                            exit 1
                        else
                            echo "App is reachable!"
                            docker rm -f weather-test
                        fi
                    '''
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', "${DOCKER_HUB_CREDENTIALS}") {
                        docker.image("${DOCKER_IMAGE_TAG}:${IMAGE_TAG}").push()
                        docker.image("${DOCKER_IMAGE_TAG}:latest").push()
                    }
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent([DEPLOY_SSH_CREDENTIALS]) {
                    sh """
                        echo "Deploying Docker container on EC2..."
                        ssh -o StrictHostKeyChecking=no ${TARGET_EC2} '
                        cd /home/ubuntu/weather-app
                        docker compose down
                        docker compose pull
                        docker compose up -d --no-build
                        docker image prune -f
                        '
                    """
                }
            }
        }
    }

    post {
        always { sh 'docker image prune -f' }
        success {
            echo "Pipeline completed successfully!"
            slackSend(
                channel: 'succeeded-build',
                color: 'good',
                message: "Pipeline *${env.JOB_NAME}* #${env.BUILD_NUMBER} succeeded!\n<${env.BUILD_URL}|View Build>"
            )
        }
        failure {
            echo "Pipeline failed. Check the logs."
            slackSend(
                channel: 'devops-alerts',
                color: 'danger',
                message: "Pipeline *${env.JOB_NAME}* #${env.BUILD_NUMBER} failed!\n<${env.BUILD_URL}|View Build>"
            )
        }
    }
}
