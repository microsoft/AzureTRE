---
title: Legacy Airlock Migration Guardrails
description: Safe procedure for disabling legacy v1 airlock support without data loss
author: Microsoft
ms.date: 2026-07-13
ms.topic: how-to
keywords:
  - airlock
  - migration
  - safety
  - legacy
  - guardrails
estimated_reading_time: 5
---

## Summary

Use this runbook before setting `enable_legacy_airlock=false`.

Disabling legacy airlock removes the v1 storage infrastructure. If active v1 workspaces or in-flight v1 airlock requests still exist, this can cause data loss or workflow failures.

## Required Configuration

When you disable legacy airlock in config, set these values together:

```yaml
tre:
  enable_legacy_airlock: false
  acknowledge_legacy_airlock_disable_prerequisites: true
  block_disable_legacy_airlock_if_v1_exists: true
```

The acknowledgement setting is a Terraform guardrail to make disablement explicit.

The blocking setting is an API startup guardrail that fails fast when active v1 dependencies are still present.

## Pre-Change Checklist

1. Confirm all active workspaces are on `airlock_version=2`.
2. Confirm no in-flight v1 airlock requests remain.
3. Confirm any required legacy airlock data has been migrated or archived.
4. Set `acknowledge_legacy_airlock_disable_prerequisites=true` in config.
5. Set `block_disable_legacy_airlock_if_v1_exists=true` in config for strict enforcement.

## Expected Guardrail Behavior

If `enable_legacy_airlock=false` and v1 dependencies exist:

* Terraform validation fails unless acknowledgement is explicitly set to true.
* API startup logs a warning with v1 workspace and request counts.
* API startup fails when `block_disable_legacy_airlock_if_v1_exists=true`.

## Rollback Guidance

If guardrails trigger unexpectedly during rollout:

1. Re-enable legacy airlock by setting `enable_legacy_airlock=true`.
2. Complete migration of remaining v1 workspaces and requests.
3. Repeat the checklist and re-run deployment.
