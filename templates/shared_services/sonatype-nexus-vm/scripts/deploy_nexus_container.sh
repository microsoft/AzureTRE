#!/bin/bash

docker_pull_timeout=10

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

# Deduce memory available to Java. Either 3/4 of the system RAM, or a set minimum
# shellcheck disable=SC2002
mem_total_mb=$(( $(cat /proc/meminfo | head -1 | awk '{ print $2 }') / 1024 ))
java_mem=2703
if [ $mem_total_mb -gt 4096 ]; then
  java_mem=$(( mem_total_mb * 3 / 4 ))
fi

echo "System memory: ${mem_total_mb} MB. Java memory: ${java_mem} MB"

docker run -d -p 80:8081 -p 443:8443 -p 8083:8083 -v /etc/nexus-data:/nexus-data \
    -e INSTALL4J_ADD_VM_PARAMS="-Xmx${java_mem}m -Xms${java_mem}m" \
    --restart always \
    --name nexus \
    --log-driver local \
    sonatype/nexus3
