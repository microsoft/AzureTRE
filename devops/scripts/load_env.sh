#!/bin/bash
set -e

if [ ! -f $1 ]; then
  echo -e "\e[31m»»» 💥 Unable to find $1 file, please create file and try again!"
  exit
else
  export $(egrep -v '^#' $1 | xargs)
fi