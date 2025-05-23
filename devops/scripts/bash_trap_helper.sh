#!/bin/bash

#
# allows multiple commands to be registered and called on shell exit
# https://stackoverflow.com/questions/3338030/multiple-bash-traps-for-the-same-signal
#
function add_exit_trap() {

  local new_command=$1

  local existing_command
  existing_command=$(trap -p EXIT | sed "s/trap -- '\(.*\)' EXIT/\1/")

  if [[ -n "$existing_command" ]]; then
    # shellcheck disable=SC2064 # we want variables to expand now
    trap "${existing_command}; ${new_command}" EXIT
  else
    # shellcheck disable=SC2064 # we want variable to expand now
    trap "$new_command" EXIT
  fi

}
