#!/bin/bash
set -e

if [ ! -f $1 ]; then
  if [ -z $USE_ENV_VARS_NOT_FILES ]; then
    echo -e "\e[31m»»» 💥 Unable to find $1 file, please create file and try again!"
    #exit
  fi
else
  export $(egrep -v '^#' $1 | sed 's/.*=/TF_VAR_\L&/' | xargs)
fi