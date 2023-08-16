#!/bin/bash

docker_pull_timeout=30

while true; do
  if [ $docker_pull_timeout == 0 ]; then
    echo 'ERROR - Timeout while waiting for sonatype/nexus3 to be pulled from Docker Hub'
    exit 1
  fi

  if docker pull sonatype/nexus3; then
      echo "Image pulled successfully"
      break
  else
      echo "Failed to pull image, restarting Docker service"
      systemctl restart docker.service
      sleep 60
  fi

  ((docker_pull_timeout--));
done

docker run -d -p 80:8081 -p 443:8443 -p 8083:8083 -v /etc/nexus-data:/nexus-data \
    --restart always \
    --name nexus \
    --log-driver local \
    sonatype/nexus3
