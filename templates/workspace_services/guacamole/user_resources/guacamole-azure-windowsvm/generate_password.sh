#!/bin/bash

PASSWORD="$(LC_ALL=C tr -dc 'A-Za-z0-9_%@' </dev/urandom | head -c 16 ; echo)"
echo "{ \"password\": \"$PASSWORD\" }"
