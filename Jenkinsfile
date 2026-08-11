pipeline {
    agent any

    environment {
        // Dépôt d'images cible (à adapter : Docker Hub, GHCR, registry interne…)
        REGISTRY = 'futurekawa'
        // Bases de test provisionnées par le conteneur Postgres de la pipeline.
        // Port hôte 5433 (évite le conflit avec le Postgres de dev sur 5432).
        // host.docker.internal : adresse de l'hôte vue DEPUIS le conteneur Jenkins
        // (Docker Desktop macOS/Windows). Les tests tournent dans ce conteneur.
        TEST_DATABASE_URL_LOCAL = 'postgresql+psycopg2://futurekawa:futurekawa@host.docker.internal:5433/futurekawa_local_test'
        TEST_DATABASE_URL_CENTRAL = 'postgresql+psycopg2://futurekawa:futurekawa@host.docker.internal:5433/futurekawa_central_test'
        // Artefacts livrables de la démo
        ARTEFACTS_DIR = 'artefacts'
        // Tag d'image Docker (horodaté pour tracer la livraison)
        IMAGE_TAG = "${BUILD_ID}-${GIT_COMMIT.take(7)}"
    }

    stages {
        stage('Récupération du code') {
            steps {
                checkout scm
            }
        }

        stage('Provisionnement des bases de test') {
            steps {
                script {
                    // Conteneur Postgres partagé : user/mdp futurekawa, port hôte 5433
                    // (5432 laissé libre pour le Postgres de dev). Deux bases de test créées.
                    sh """
                        docker rm -f futurekawa-testdb 2>/dev/null || true
                        docker run -d --name futurekawa-testdb -p 5433:5432 \
                          -e POSTGRES_USER=futurekawa -e POSTGRES_PASSWORD=futurekawa \
                          -e POSTGRES_DB=futurekawa postgres:16-alpine
                        # On attend que Postgres soit prêt avant de créer les bases de test.
                        for i in \$(seq 1 30); do
                          docker exec futurekawa-testdb pg_isready -U futurekawa -q && break
                          sleep 1
                        done
                        docker exec futurekawa-testdb psql -U futurekawa -d futurekawa -c "CREATE DATABASE futurekawa_local_test;"
                        docker exec futurekawa-testdb psql -U futurekawa -d futurekawa -c "CREATE DATABASE futurekawa_central_test;"
                    """
                }
            }
        }

        stage('Qualité du code (ruff)') {
            steps {
                script {
                    // Environnements virtuels locaux (mêmes chemins que scripts/test-*.sh)
                    sh 'cd local-country/backend && python3 -m venv ../.venv && ../.venv/bin/pip install -q -r requirements.txt'
                    sh 'cd central-backend && python3 -m venv venv && venv/bin/pip install -q -r requirements.txt'
                    sh 'cd local-country/backend && ../.venv/bin/ruff check app main.py tests && ../.venv/bin/ruff format --check app main.py tests'
                    sh 'cd central-backend && venv/bin/ruff check app tests && venv/bin/ruff format --check app tests'
                }
            }
        }

        stage('Tests automatisés') {
            parallel {
                stage('Backend local (Colombie)') {
                    steps {
                        sh 'cd local-country/backend && TEST_DATABASE_URL=${TEST_DATABASE_URL_LOCAL} ../.venv/bin/python -m pytest -v --tb=short'
                    }
                }
                stage('Backend central (Siège)') {
                    steps {
                        sh 'cd central-backend && TEST_DATABASE_URL=${TEST_DATABASE_URL_CENTRAL} venv/bin/python -m pytest -v --tb=short'
                    }
                }
                stage('Frontend central') {
                    steps {
                        sh 'cd central-frontend && npm ci && npm run test -- --run'
                        sh 'cd central-frontend && npm run build'
                    }
                }
            }
        }

        stage('Packaging images Docker') {
            steps {
                script {
                    // Positionnement dans le contexte de build : image locale reste buildable aussi.
                    sh "cd local-country/backend && docker build -t ${REGISTRY}/futurekawa-country-api:${IMAGE_TAG} -t ${REGISTRY}/futurekawa-country-api:latest ."
                    sh "cd central-backend && docker build -t ${REGISTRY}/futurekawa-central-backend:${IMAGE_TAG} -t ${REGISTRY}/futurekawa-central-backend:latest ."
                    sh "cd central-frontend && npm run build"
                    sh "cd central-frontend && (test -d dist || echo 'dist absent')"
                }
            }
        }

        stage('Livraison des artefacts (démo)') {
            steps {
                sh '''
                    rm -rf ${ARTEFACTS_DIR} && mkdir -p ${ARTEFACTS_DIR}/images ${ARTEFACTS_DIR}/frontend ${ARTEFACTS_DIR}/rapports
                    # Images Docker exportées (livrables hors-ligne)
                    docker save -o ${ARTEFACTS_DIR}/images/futurekawa-country-api_${IMAGE_TAG}.tar ${REGISTRY}/futurekawa-country-api:${IMAGE_TAG}
                    docker save -o ${ARTEFACTS_DIR}/images/futurekawa-central-backend_${IMAGE_TAG}.tar ${REGISTRY}/futurekawa-central-backend:${IMAGE_TAG}
                    # Build frontal embarqué (réutilisable sans serveur Node)
                    if [ -d central-frontend/dist ]; then
                       cp -r central-frontend/dist ${ARTEFACTS_DIR}/frontend/
                    fi
                    # Rapports de tests si générés par l'agent (junit.xml optionnel)
                    find . -name 'junit.xml' -exec cp {} ${ARTEFACTS_DIR}/rapports/ \\; 2>/dev/null || true
                '''
                archiveArtifacts artifacts: "${ARTEFACTS_DIR}/**/*"
                // Listage final pour traçabilité
                sh 'ls -lhR ${ARTEFACTS_DIR}'
            }
        }
    }

    post {
        always {
            // Empêche de laisser le conteneur Postgres de test en vie sur l'agent.
            sh 'docker rm -f futurekawa-testdb 2>/dev/null || true'
        }
        success {
            echo "Pipeline OK — artefact de preuve d'exécution : ${ARTEFACTS_DIR}/ (journal complet dans l'historique du build)."
        }
        failure {
            echo "Pipeline en échec : consultez le journal du build dans Jenkins."
        }
    }
}