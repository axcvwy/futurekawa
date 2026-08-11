FROM jenkins/jenkins:lts

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        nodejs \
        npm \
        docker.io \
        docker-cli \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g npm@10

RUN usermod -aG docker jenkins

USER jenkins
