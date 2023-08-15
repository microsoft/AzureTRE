#!/bin/bash

while true; do
    docker pull sonatype/nexus3
    if [ $? -eq 0 ]; then
        echo "Image pulled successfully"
        break
    else
        echo "Failed to pull image, restarting Docker service"
        systemctl restart docker.service
        sleep 60
    fi
done
