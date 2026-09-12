# Claude Code instructions

Read and follow the repository-wide guidance in [`AGENTS.md`](AGENTS.md).

Use the nearest subsystem instructions when they exist. For PR validation against Azure, load `.claude/skills/pr-tester/SKILL.md`; do not invent deployment or testing sequences. Keep the approval boundaries in `AGENTS.md`: external side effects, shared-environment tests, publishing, deployment, and destruction require explicit authorization.
