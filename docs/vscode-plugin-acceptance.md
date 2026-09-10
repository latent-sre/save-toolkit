# VS Code plugin acceptance

Run this against the candidate plugin in an authorized test session, using a neutral project and
an isolated VS Code profile. No production connection or credential-bearing command is needed.
Keep the session transcript private; record only the observations supporting each result.

## Bind the installation

Record the output of code --version, the Copilot extension version, the selected model, the
candidate commit and plugin source digest. Use Chat: Install Plugin From Source for a published
candidate, or chat.pluginLocations pointing at its absolute directory for a local candidate.
Enable chat.plugins.enabled. Open a neutral project: opening this repository can discover its
workspace agents and hide an installation defect. Enable one copy of Save Toolkit.

The [official plugin guide](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
owns current installation syntax. Source declarations alone do not establish runtime enforcement.

## Acceptance cases

| Case | Exercise and evidence required |
|---|---|
| Discovery | Confirm eight named agents and the current skill set from the plugin location. Record the effective tools for reviewer, researcher and sre-assistant; the last must have no execute tool. |
| Installed helper | Select obs-dashboards and ask it to run its bundled hygiene helper with --help. Confirm the invoked absolute path lies in the installed skill, and run succeeds from the neutral project. A project file with the same relative name must not be selected. |
| Allowed child and return | Assign software-engineer a tiny fixture change followed by a reviewer check. The dispatch must name the caller, human owner, bounded question and return recipient. Inspect a completed reviewer invocation and the parent's subsequent response to the human. |
| Forbidden child | In a disposable synthetic plugin, give a parent the agent tool with an allowlist containing only probe-allowed. Ask for probe-forbidden, a second harmless child. A host refusal must occur before invocation. Remove the synthetic plugin afterward. A prose refusal without an attempted host check proves only model behavior. |
| Human incident exchange | In incident-investigation, ask for one helper slice from supplied synthetic observations: aggregate crash count, one timestamped change, no crash timestamps. Require a real sre-assistant return. The parent must preserve unknown event ordering and avoid turning recipient readback time into observation time or correlation into cause. |
| Missing evidence | Supply no accessible platform source. The helper must return the missing source and the human console view to check; the parent must continue with a useful next question, without inventing live observations or closing the incident. |
| Lifecycle | Disable the plugin and confirm its components disappear from a fresh session. Re-enable and then uninstall the disposable installation; confirm no duplicate workspace copy conceals either result. |

Do not use the real security boundary as the negative fixture: all synthetic children are
harmless and have no effectful tools. Each record retains the exact input, actual tool/child result,
final human-facing answer, target identity, and PASS/FAIL/UNVERIFIED with its reason.

## Hook limitation and release

VS Code 1.111+ supports agent-scoped hooks whose `PreToolUse` may return a permission decision,
but this plugin ships `hooks/copilot-hooks.json` empty. Do not claim Claude's guard is present.
Before proposing one, use a separate disposable agent-scoped hook that denies a harmless command,
and a built-in Agent control that remains unaffected. This canary grants no cloud access.

A supported release needs these cases on the shipping bytes and a reviewed rollback:
the release owner assigns a consistent version to the manifests and marketplace, binds the tested
artifact to an immutable selector/checksum, and verifies reinstalling the previously accepted
artifact. Follow [release readiness](../skills/production-change-gate/references/release-readiness.md)
and its distribution-specific immutability evidence. A mutable main install remains pre-release.

Record results under the RELEASE-001 item in the [live roadmap](fleet-roadmap.md). Source tests and
an installed VS Code version number do not close runtime or model-behavior gaps.
