#!/bin/bash

sudo chgrp docker /var/run/docker.sock
sudo chmod g+rw /var/run/docker.sock
