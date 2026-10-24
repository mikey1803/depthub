// DeptHub CI/CD pipeline:
//   Checkout -> Install & Test -> Validate Data -> Build Package -> Deploy to Azure
//
// Needs on the Jenkins machine (Linux): git, python3 + python3-venv, ssh/scp, tar.
// Needs in Jenkins: credential 'azure-vm-ssh' (SSH private key), plugins listed in README.
// Optional global environment variables (Manage Jenkins > System):
//   AZURE_VM_IP  - VM address, used when the VM_IP parameter is empty
//   NOTIFY_EMAIL - who gets the success / failure emails
pipeline {
    agent any

    parameters {
        string(name: 'VM_IP', defaultValue: '',
               description: 'Public IP of the Azure VM (terraform output public_ip_address). Empty = use the AZURE_VM_IP environment variable.')
        string(name: 'VM_USER', defaultValue: 'azureuser',
               description: 'SSH user on the VM')
        string(name: 'SSH_PORT', defaultValue: '',
               description: 'SSH port on the VM. Empty = use AZURE_SSH_PORT, or 22 if that is not set.')
        booleanParam(name: 'SKIP_CHECKS', defaultValue: false,
               description: 'DEMO ONLY: skip tests and data validation so a bad commit reaches the VM and the auto-rollback can be shown.')
    }

    triggers {
        githubPush()               // GitHub webhook (instant)
        pollSCM('H/2 * * * *')     // fallback: check GitHub every ~2 minutes
    }

    options {
        disableConcurrentBuilds()  // two deploys at once would fight over the same VM
        timeout(time: 20, unit: 'MINUTES')
    }

    environment {
        DEPLOY_HOST = "${params.VM_IP ?: (env.AZURE_VM_IP ?: '')}"
        // SSH port: 22, or 443 on networks that block outgoing port 22 (set AZURE_SSH_PORT)
        SSH_PORT    = "${params.SSH_PORT ?: (env.AZURE_SSH_PORT ?: '22')}"
        // Parameters are empty on the very first build (Jenkins has not read them yet), so always fall back
        SSH_USER    = "${params.VM_USER ?: 'azureuser'}"
        SSH_OPTS    = '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        PACKAGE     = "depthub-${env.BUILD_NUMBER}.tar.gz"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.COMMIT_MSG    = sh(script: 'git log -1 --pretty=%s',  returnStdout: true).trim()
                    env.COMMIT_AUTHOR = sh(script: 'git log -1 --pretty=%an', returnStdout: true).trim()
                    env.COMMIT_SHORT  = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                }
                echo "Building ${env.COMMIT_SHORT}: ${env.COMMIT_MSG} (by ${env.COMMIT_AUTHOR})"
            }
        }

        stage('Install & Test') {
            when { expression { !params.SKIP_CHECKS } }
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet -r requirements-dev.txt
                    pytest -q
                '''
            }
        }

        stage('Validate Data') {
            when { expression { !params.SKIP_CHECKS } }
            steps {
                // Fails the build (exit code 1) if notices.json / students.json are wrong
                sh 'python3 scripts/validate_data.py'
            }
        }

        stage('Build Package') {
            steps {
                sh '''
                    python3 scripts/make_version.py
                    tar -czf "$PACKAGE" --exclude='__pycache__' \
                        app.py requirements.txt version.json data scripts static templates
                '''
                archiveArtifacts artifacts: 'depthub-*.tar.gz', fingerprint: true
            }
        }

        stage('Deploy to Azure') {
            steps {
                script {
                    if (!env.DEPLOY_HOST) {
                        error('No VM address. Set the VM_IP parameter or the AZURE_VM_IP environment variable.')
                    }
                }
                sshagent(credentials: ['azure-vm-ssh']) {
                    sh 'scp -P "$SSH_PORT" $SSH_OPTS "$PACKAGE" scripts/deploy.sh "$SSH_USER@$DEPLOY_HOST:/tmp/"'
                    script {
                        // deploy.sh exits 1 when the new release failed its health check (and was rolled back).
                        // Any other failure code (e.g. 255 = cannot connect) means the script never judged the release.
                        def rc = sh(returnStatus: true,
                                    script: 'ssh -p "$SSH_PORT" $SSH_OPTS "$SSH_USER@$DEPLOY_HOST" "bash /tmp/deploy.sh $BUILD_NUMBER /tmp/$PACKAGE"')
                        if (rc == 1) {
                            env.ROLLED_BACK = 'true'
                            error('deploy.sh reported a failed deploy: the previous version is still live (rolled back).')
                        } else if (rc != 0) {
                            error("ssh to the VM failed with exit code ${rc}.")
                        }
                    }
                }
            }
        }
    }

    post {
        success {
            script {
                if (env.NOTIFY_EMAIL) {
                    emailext(
                        to: env.NOTIFY_EMAIL,
                        subject: "New DeptHub deploy live: v${env.BUILD_NUMBER}",
                        body: """DeptHub v${env.BUILD_NUMBER} is live.

Commit:  ${env.COMMIT_SHORT}
Message: ${env.COMMIT_MSG}
Author:  ${env.COMMIT_AUTHOR}
Site:    http://${env.DEPLOY_HOST}/
Build:   ${env.BUILD_URL}
"""
                    )
                } else {
                    echo 'NOTIFY_EMAIL is not set, skipping the success email.'
                }
            }
        }
        failure {
            script {
                if (env.NOTIFY_EMAIL) {
                    // Only claim a rollback if deploy.sh itself reported the failed deploy
                    def what = 'The build failed before the new version went live, so the live site was not changed.'
                    if (env.ROLLED_BACK == 'true') {
                        what = 'The deploy failed its health check and the site was rolled back to the last working version.'
                    }
                    emailext(
                        to: env.NOTIFY_EMAIL,
                        subject: "DeptHub deploy FAILED: build #${env.BUILD_NUMBER}",
                        body: """${what}

Commit:  ${env.COMMIT_SHORT ?: 'unknown'}
Message: ${env.COMMIT_MSG ?: 'unknown'}
Author:  ${env.COMMIT_AUTHOR ?: 'unknown'}
Site:    http://${env.DEPLOY_HOST}/
Console: ${env.BUILD_URL}console
"""
                    )
                } else {
                    echo 'NOTIFY_EMAIL is not set, skipping the failure email.'
                }
            }
        }
    }
}
