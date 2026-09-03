---
name: migrate-to-builds
description: >-
  Test that a Cloud Agent environment will work with prebuilt environment builds
  and recommend any required changes. Use when the user wants to migrate to
  builds, test build compatibility, or follow the Builds page setup-agent flow.
environments:
  - cloud
metadata:
  environments:
    - cloud
---
# Migrate an Environment to Builds

Use this skill when the user wants to test that the current Cloud Agent environment will work with environment builds, or asks to migrate to builds. Do not enable builds yourself; the user enables them on the Builds tab after review.

## Resources

| Workflow | Reference |
| --- | --- |
| Migrate an existing environment to builds | [Migrate an environment to builds](references/migrate-to-builds.md) |

## Choose the workflow

Read [Migrate an environment to builds](references/migrate-to-builds.md) and follow it. Call `environment-info` first when available so the reference can classify repository-managed vs DB-managed configuration.

## Mental Model

A Cloud Agent starts in an isolated remote machine. Its environment has two layers:

1. **Base environment**: a saved snapshot, Dockerfile-built image, explicit image, or Codex's default image supplies the operating system, system packages, and toolchains.
2. **Repository bootstrap**: after Codex checks out the selected repository revision, `install` refreshes project dependencies and generated state. `start` and `terminals` then start services needed while the agent works.

With environment builds, `install` creates the baseline snapshot and is not rerun when a new pod boots from that build. Per-pod initialization therefore belongs in `start` or `terminals`. Without a build, setup may run `install` while preparing the agent.

Environment changes normally affect newly started agents. Do not imply that editing configuration rebuilds or migrates an already-running agent.

## Configuration Sources and Precedence

Codex resolves environment configuration in this order:

1. `.cursor/environment.json` from the repository revision used to start the agent.
2. A personal saved environment for the repository.
3. A team saved environment for the repository.

The first available source wins. Prefer the Cloud Agent environment-info tool when available; otherwise inspect the repository and explain what cannot be confirmed.

## Choosing install, start, or terminals

Classify each setup action by the lifetime of the state it creates:

| Location | Use it for | Expected behavior |
| --- | --- | --- |
| `install` | Durable repository setup tied to checked-out source: package installation, compilation, code generation, and local configuration that can be recreated. | Runs after source is available and may run again after changes or against cached state. It must be idempotent, non-interactive, and terminate successfully. No process started here should be expected to survive into a later boot. |
| `start` | Per-boot runtime initialization: starting system daemons, restoring ephemeral service state, or launching a supervised/background service required whenever the machine starts. | Runs every time the environment starts. It must tolerate restarts, avoid duplicate processes, and reach a clear success or failure state. |
| `terminals` | Long-running foreground processes the agent should see, inspect, restart, or read logs from: development servers, watchers, and workers. | Runs as named tmux-backed processes after startup. Commands may remain active for the lifetime of the environment. |

A development server does not belong in `install`: cached setup or a snapshot may preserve its files but not its process, and a foreground server can prevent installation from completing. Put it in `terminals` when the agent benefits from visible logs and direct restarts. Use `start` when a startup script launches or reconciles the service under a process manager, confirms readiness, and then returns.

### Diagnose misplaced work

When environment setup hangs, behaves differently after a snapshot, or loses services between agents:

1. Identify the phase and command from setup logs. Do not infer the failing phase from the script name alone.
2. Ask whether the command creates durable files or requires a live process.
3. If `install` launches a server, watcher, worker, Docker daemon, or other process that must still be running later, move that responsibility to `start` or `terminals`.
4. If `start` repeatedly installs packages, compiles the repository, or regenerates source-derived files, move that responsibility to `install`.
5. Make the destination idempotent and validate with a build plus fresh-agent smoke test when tools allow.

Typical signals:

- **Install never completes:** a foreground server or interactive command is running in `install`.
- **Files exist but the service disappears on a later boot:** the service was started during `install` and its process was not part of durable state.
- **Every boot is slow or changes the lockfile:** dependency setup is incorrectly running in `start`.
- **Start fails with “address already in use” or duplicate workers:** the start path is not idempotent.

## Safety

- Never put tokens, passwords, private keys, or secret values in `environment.json`, Dockerfiles, committed scripts, logs, or chat output. Use supported environment secrets or build-secret mechanisms.
- Do not deploy, publish, apply infrastructure, or mutate production resources as part of environment setup.
- Keep Dockerfiles and install scripts deterministic, non-interactive, and narrowly scoped.
- Do not weaken network, certificate, or package-integrity controls merely to make setup pass.
- Avoid expensive rebuilds until static checks pass. Trigger a build only when the migrate reference says to. Unrelated questions never do.
- Do not enable builds for the environment and do not ask the user to promote, activate, merge, or save a draft as the primary next step.

## Response

Lead with the outcome. Include only the sections relevant to the request:

- Effective configuration source and whether it is repository-managed or DB-managed.
- What was inspected or changed.
- Build and fresh-agent validation evidence.
- Remaining manual action: usually enabling builds on the Builds tab.

When mentioning an environment or build ID in chat, use a markdown hyperlink whose link text is the ID — never a bare ID:

- Environment: `[<environmentPublicId>](https://cursor.com/dashboard/cloud-agents/environments/e/<environmentPublicId>)`
- Environment Builds tab (when directing the user to enable builds or review build status): `[<environmentPublicId>](https://cursor.com/dashboard/cloud-agents/environments/e/<environmentPublicId>#builds)` or an "environment dashboard" link to the same URL
- Build: `[<buildId>](https://cursor.com/dashboard/cloud-agents/builds/<buildId>)`

Prefer the environment `url` from environment-info when present; otherwise construct the environment link with the format above. When the user should land on the Builds tab, append `#builds` to that URL if it has no hash yet.
