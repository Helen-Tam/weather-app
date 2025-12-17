pipeline {
    agent {
        kubernetes {
            label 'jenkins-agent'
            defaultContainer 'jnlp'
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: jenkins-docker-agent
spec:
  containers:
  - name: jnlp
    image: jenkins/inbound-agent
    args: ['$(JENKINS_SECRET)', '$(JENKINS_NAME)']
    volumeMounts:
      - name: workspace-volume
        mountPath: /home/jenkins/agent

  - name: pylint-agent
    image: idandror/jenkins-agent:latest
    command:
      - cat
    tty: true
    volumeMounts:
      - name: workspace-volume
        mountPath: /home/jenkins/agent

  - name: docker
    image: docker:24-dind
    securityContext:
      privileged: true
    env:
      - name: DOCKER_TLS_CERTDIR
        value: ""
    volumeMounts:
      - name: docker-graph
        mountPath: /var/lib/docker
      - name: workspace-volume
        mountPath: /home/jenkins/agent

  volumes:
    - name: workspace-volume
      emptyDir: {}
    - name: docker-graph
      emptyDir: {}
'''
        }
    }

    environment {
        GITLAB_URL = 'https://gitlab.helen-tam.org/root/weather.git' // replace with actual private IP
        DOCKER_IMAGE_TAG = "helentam93/weather:latest"
        DOCKER_HUB_CREDENTIALS = 'dockerhub-creds'
    }



    stages {
        stage('Clone Repo') {

            steps {
              container('jnlp') {
                echo 'Cloning repository from GitLab...'
                checkout scm
              }
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

        stage('Build and Test Docker Image') {
            steps {
                container('docker') {
                    script {
                            sh """
                            echo "Waiting for Docker daemon..."
                            until docker info >/dev/null 2>&1; do sleep 2; done

                            echo "Building Docker image..."
                            docker build -t ${DOCKER_IMAGE_TAG} .

                            echo "Testing Docker image reachability..."
                            # Start a container in detached mode
                            docker run -d --name temp-test-container -p 5000:5000 ${DOCKER_IMAGE_TAG}

                            # Wait for the app to start
                            sleep 5

                            # Reachability test
                            curl -f http://localhost:5000 || { echo "Reachability test FAILED"; docker logs temp-test-container; docker rm -f temp-test-container; exit 1; }

                            echo "Reachability test SUCCESS"

                            # Stop and remove the test container
                            docker rm -f temp-test-container

                            """

                    }
                }
            }
        }
    }


    post {
        always {
            container('docker') {
                sh 'docker image prune -f'
            }
        }
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

