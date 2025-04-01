pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo "Building branch: ${env.BRANCH_NAME}"
            }
        }

        stage('Test') {
            steps {
                echo "Running tests for ${env.BRANCH_NAME}"
            }
        }

        stage('Deploy') {
            when { branch 'main' } // Only deploy if on the main branch
            steps {
                echo "Deploying to production"
            }
        }
    }
}
