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

  - name: main-agent
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
        GITOPS_REPO = "https://github.com/Helen-Tam/gitops-weather-app.git"
        GITOPS_DIR  = "gitops-weather-app"

        DOCKER_REPO = "helentam93/weather"
        IMAGE_TAG   = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
        DOCKER_IMAGE = "${DOCKER_REPO}:${IMAGE_TAG}"

        DOCKER_HUB_CREDENTIALS = 'dockerhub-creds'
        GIT_CREDENTIALS       = 'git-creds'
    }

    stages {

        stage('Clone App Repo') {
            steps {
                container('jnlp') {
                    echo "Cloning application repository..."
                    checkout scm
                }
            }
        }

        stage('Static Code Analysis') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'staging'
                }
            }
            steps {
                container('main-agent') {
                    sh '''
                      echo "Running pylint on app.py..."
                      SCORE=$(pylint app.py | awk '/rated at/ {print $7}' | cut -d'/' -f1)
                      echo "Pylint score: $SCORE"
                      (( $(echo "$SCORE < 7.0" | bc -l) )) && exit 1 || echo "Score OK"
                    '''
                }
            }
        }

        stage('TruffleHog Secret Scan') {
            steps {
                container('main-agent') {
                  sh '''
                      echo "Create virtual environment..."
                      python3 -m venv venv
                      . venv/bin/activate

                      echo "Installing truffleHog..."
                      pip install --upgrade pip
                      pip install truffleHog

                      echo "Running secret scan..."
                      trufflehog discover --repo_path . --json --max_depth 10
                  '''
                }
            }
        }

        stage('Dependency Scan for Python') {
            steps {
                container('docker') {
                    sh '''
                        echo "Running the dependency file-system scan..."
                        docker run --rm -v $(pwd):/src aquasec/trivy:latest fs \
                          --exit-code 1 --severity CRITICAL /src

                        echo "Scanning Dockerfile ..."
                        docker run --rm -v $(pwd):/src aquasec/trivy:latest config \
                          --exit-code 1 --severity CRITICAL /src/Dockerfile
                    '''
                }
            }
        }

        stage('Build and Test Docker Image') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'staging'
                    branch 'main'
                }
            }
            steps {
                container('docker') {
                    sh '''
                        echo "Waiting for Docker daemon..."
                        until docker info >/dev/null 2>&1; do sleep 2; done

                        echo "Building Docker image..."
                        docker build -t $DOCKER_IMAGE .

                        echo "Scanning Built Image for OS Vulnerabilities..."
                        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                            aquasec/trivy:latest image \
                            --exit-code 1 --severity CRITICAL $DOCKER_IMAGE

                        echo "Running container for test..."
                        docker run -d --name test-container -p 8000:8000 $DOCKER_IMAGE
                        sleep 5

                        echo "Testing application reachability..."
                        if curl -f http://localhost:8000; then
                            echo "Reachability test PASSED"
                        else
                            echo "Reachability test FAILED"
                            exit 1
                        fi

                        echo "Stopping the test container..."
                        docker stop test-container
                        docker rm test-container
                    '''
                }
            }
        }

        stage('Push and Sign Image') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'staging'
                    branch 'main'
                }
            }
            steps {
                container('docker') {
                    withCredentials([usernamePassword(
                        credentialsId: "${DOCKER_HUB_CREDENTIALS}", 
                        usernameVariable: 'DOCKER_USER', 
                        passwordVariable: 'DOCKER_PASS'),
                        file(credentialsId: 'cosign-key', variable: 'COSIGN_KEY_FILE')
                    ]) {
                        sh '''
                            echo "Logging into Docker Hub..."
                            echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin

                            echo "Pushing Image..."
                            docker push $DOCKER_IMAGE

                            echo "Identifying Image Digest..."
                            IMAGE_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' $DOCKER_IMAGE)
                            echo $IMAGE_DIGEST > image-digest.txt
                            echo "Image digest: $IMAGE_DIGEST"

                            echo "Signing Digest: $IMAGE_DIGEST"

                            if [ "$BRANCH_NAME" != "develop" ]; then
                                echo "Installing Cosign..."
                                curl -LO https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64
                                chmod +x cosign-linux-amd64
                                mv cosign-linux-amd64 /usr/local/bin/cosign

                                echo "Signing image digest..."
                                cosign sign --key $COSIGN_KEY_FILE --tlog-upload=false $IMAGE_DIGEST
                            else
                                echo "Skipping image signing for develop"
                            fi
                        '''
                    }
                }
            }
        }

        stage('Update Helm Chart in GitOps Repo') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'staging'
                    branch 'main'
                }
            }
            steps {
                container('jnlp') {
                    script {
                        def envName = ""
                        if (env.BRANCH_NAME == 'develop') {
                            envName = "dev"
                        } else if (env.BRANCH_NAME == 'staging') {
                            envName = "staging"
                        } else if (env.BRANCH_NAME == 'main') {
                            envName = "prod"
                        } else {
                            echo "Feature/Hotfix branch detected, skipping Helm update."
                            envName = null
                        }

                        if (envName) {
                            echo "Updating Helm values for environment: ${envName}"

                            withCredentials([usernamePassword(
                                credentialsId: "${GIT_CREDENTIALS}",
                                usernameVariable: 'GIT_USER',
                                passwordVariable: 'GIT_TOKEN'
                            )]) {
                                sh """
                                    rm -rf ${GITOPS_DIR}
                                    git clone https://${GIT_USER}:${GIT_TOKEN}@github.com/Helen-Tam/gitops-weather-app.git ${GITOPS_DIR}
                                    cd ${GITOPS_DIR}
                                    git config user.email "jenkins@ci.local"
                                    git config user.name "Jenkins CI"

                                    cd weather-app

                                    if [ "$BRANCH_NAME" = "develop" ]; then
                                        echo "Updating tag for dev"
                                        yq e '.image.tag = "${IMAGE_TAG}" | .image.digest = ""' -i values-${envName}.yaml
                                    else
                                        echo "Updating digest for ${envName}"
                                        DIGEST=$(cut -d@ -f2 ../../image-digest.txt)
                                        yq e '.image.digest = "'$DIGEST'" | .image.tag = ""' -i values-${envName}.yaml
                                    fi

                                    git add values-${envName}.yaml
                                    if git diff --cached --quiet; then
                                        echo "No GitOps changes detected; skipping commit."
                                    else
                                        git commit -m "Update image reference for ${envName}"
                                        git push origin main
                                    fi
                                """
                            }
                        }
                    }
                }
            }
        }
    }


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
