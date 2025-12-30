pipeline {
    agent {
        kubernetes {
            label 'jenkins-agent'
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
        GITLAB_CREDENTIALS = 'git-lab-key'

        DOCKER_REPO = "helentam93/weather"
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
        DOCKER_IMAGE = "${DOCKER_REPO}:${IMAGE_TAG}"
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
              container('pylint-agent') {
                sh '''
                    echo "Running pylint on app.py..."
                    SCORE=$(pylint app.py | awk '/rated at/ {print $7}' | cut -d'/' -f1)
                    echo "Pylint score: $SCORE"
                    (( $(echo "$SCORE < 5.0" | bc -l) )) && exit 1 || echo "Score OK"
                '''
              }
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
                            docker build -t ${DOCKER_IMAGE} .

                            echo "Installing curl..."
                            apk add --no-cache curl

                            echo "Running container for test..."
                            docker run -d --name test-container -p 8000:8000 ${DOCKER_IMAGE}
                            sleep 5

                            echo "Testing application reachability..."
                            if curl -f http://localhost:8000; then
                                echo "Reachability test PASSED"
                            else
                                echo "Reachability test FAILED"
                                exit 1
                            fi
                            """
                    }
                }
            }
        }

        stage('Push to DockerHub') {
            steps {
                container('docker') {
                    withCredentials([usernamePassword(
                        credentialsId: "${DOCKER_HUB_CREDENTIALS}",
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS')]) {
                      sh """
                        echo "Logging into Docker Hub..."
                        echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin
                        echo "Pushing Docker image ${DOCKER_IMAGE}..."
                        docker push ${DOCKER_IMAGE}
                      """
                    }
                }
            }
        }
    }

//         stage('Update image tag in the Helm Chart') {
//             steps {
//                 container('jnlp') {
//                     script {
//                         withCredentials([usernamePassword(
//                             credentialsId: 'git-lab-key',
//                             usernameVariable: 'GIT_USER',
//                             passwordVariable: 'GIT_TOKEN')]) {
//                           sh """
//                             echo "Updating Helm values.yaml image tag to ${IMAGE_TAG}"
//                             ls -l weather-app/
//                             sed -i "s/^  tag:.*/  tag: ${IMAGE_TAG}/" weather-app/values.yaml
//
//                             # Push the changes bask to the repository
//                             git add weather-app/values.yaml
//                             git commit -m "Update weather image tag to ${IMAGE_TAG}" || echo "No changes to commit"
//                             git push https://$GIT_USER:$GIT_TOKEN@gitlab.helen-tam.org/root/weather-app.git HEAD:main
//                         """
//                        }
//                     }
//                 }
//             }
//         }
//     }

    post {
        always {
           container('docker') {
              sh """
                echo "Cleaning up test container if it exists..."
                docker rm -f test-container || true
              """
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

