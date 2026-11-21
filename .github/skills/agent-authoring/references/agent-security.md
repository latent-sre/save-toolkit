# Reviewing an agent's authority

Trace one task from its inputs to its possible effects. Which inputs can another party control?
Which private data or credentials can the agent or its tools access? Where can it send data or
change state? Follow these paths across handoffs as well as within a single agent. A separate
model context can still share the same tools, credentials, and network access.

For example, an agent reads incoming messages and drafts responses. If a message supplies the
recipient and the agent can send without confirmation, its content can redirect an external
action. Give a draft-only agent a draft tool. If sending is required, have the sending service
validate the destination and bind any required approval to the actual recipient and message.

Inspect the control on the action path. A typed tool argument can ensure a destination is
well-formed. The tool or service must also verify that destination is allowed. Treat instructions
in documents, retrieved text, or tool results as data. Source labels help interpretation.
Implement any required escaping and evidence preservation in the component that renders the
result. Keep secrets out of model context wherever a tool can use them at the boundary.

Separate what the artifact requests, what a trusted configuration grants, and what the installed
system enforces. A shell, another tool, or a delegate may expose the same effect. To check a
restriction, exercise a permitted case and a harmless disallowed case in an authorized test
environment. Review candidate-supplied code statically unless execution is authorized and isolated
from sensitive data and real effects.

Report a finding when evidence connects an input, a reachable capability, and a consequence.
Name the control the workflow relies on and the smallest change that closes the gap. When
deployment evidence is unavailable, state the open question, its consequence for the conclusion,
and the observation that would resolve it. For a change to an existing guard, identify which
actions become newly allowed or denied so its owner can assess the change.
