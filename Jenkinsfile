pipeline {
  agent any
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build images & Start stack') {
      steps {
        script {
          // Ensure this Jenkins node has docker and docker-compose installed and the Jenkins user has permission.
          if (fileExists('docker-compose.yml')) {
            sh 'docker-compose -f docker-compose.yml up -d --build'
          } else {
            error 'docker-compose.yml not found. Place it in the repo root.'
          }
        }
      }
    }
  }
  post {
    always {
      echo 'Pipeline finished. Inspect container logs if needed.'
    }
  }
}
