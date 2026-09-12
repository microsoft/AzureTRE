#!/usr/bin/env bash
set -euo pipefail

bundle_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
export test_dir
export RP_CLIENT_ID=test HOST_POOL_ID=test STORAGE_ACCOUNT=test LOCK_CONTAINER=test KEY_VAULT_NAME=test SECRET_NAME=test

az() {
    if [[ "$1" == login ]]; then return 0; fi
    printf '%s\n' "$3" >> "$test_dir/calls"
    local attempts
    attempts=$(grep -c "^$3$" "$test_dir/calls")
    case "$3" in
        exists)
            case "$scenario" in
                existing) echo true ;;
                delayed_access) [[ "$attempts" -gt 2 ]] || return 1; echo false ;;
                delayed_upload) echo false ;;
                concurrent_create) [[ "$attempts" -gt 1 ]] && echo true || echo false ;;
                denied) return 1 ;;
            esac
            ;;
        upload)
            [[ " $* " == *" --overwrite false "* ]] || return 2
            case "$scenario" in
                delayed_access) return 0 ;;
                delayed_upload) [[ "$attempts" -gt 2 ]] ;;
                concurrent_create) return 1 ;;
                *) return 2 ;;
            esac
            ;;
        *) return 2 ;;
    esac
}
sleep() { :; }
export -f az sleep

for script in "$bundle_dir/terraform/ensure_registration.sh" "$bundle_dir/user_resources/avd-personal-sessionhost/terraform/ensure_registration.sh"; do
    bash -n "$script"
    for scenario in existing delayed_access delayed_upload concurrent_create denied; do
        export scenario
        : > "$test_dir/calls"
        if bash <(sed '/^storage_args+=(--blob-name/,$d' "$script") > "$test_dir/output" 2>&1; then
            [[ "$scenario" != denied ]]
        else
            [[ "$scenario" == denied ]]
            grep -q 'Timed out initializing the AVD registration lock' "$test_dir/output"
            [[ $(grep -c '^exists$' "$test_dir/calls") -eq 60 ]]
        fi
        case "$scenario" in
            existing) [[ $(wc -l < "$test_dir/calls") -eq 1 ]] ;;
            delayed_access) [[ $(grep -c '^exists$' "$test_dir/calls") -eq 3 ]] ;;
            delayed_upload) [[ $(grep -c '^upload$' "$test_dir/calls") -eq 3 ]] ;;
            concurrent_create) [[ $(grep -c '^exists$' "$test_dir/calls") -eq 2 ]] ;;
        esac
        printf 'PASS: %s %s\n' "$script" "$scenario"
    done
done