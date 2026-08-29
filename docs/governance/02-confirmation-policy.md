# Confirmation Policy

Data operations, including `delete_*`, execute directly without asking for confirmation first —
that's the expected behavior in this project, to remove the friction of having to go through the
HUD's chat/voice interface. This includes the cascade effect of `delete_system` over its Projects
(and transitively the Tasks of those Projects), and of `delete_project` over its Tasks.

System changes follow the normal safety rules already in force generally (confirm before
destructive git/infrastructure actions, don't commit unless explicitly asked, etc.) — see
`memory/operational_safety.md` for the specific unsupervised-vs-needs-a-human breakdown for this
project.
