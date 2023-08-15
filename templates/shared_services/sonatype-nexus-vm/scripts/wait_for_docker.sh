#!/bin/bash

while true; do
    if docker pull sonatype/nexus3; then
        echo "Image pulled successfully"
        break
    else
        echo "Failed to pull image, restarting Docker service"
        systemctl restart docker.service
        sleep 60
    fi
done
