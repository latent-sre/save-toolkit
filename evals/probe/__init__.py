"""The eval runner behind `evals/build_probe.py`, one module per job, in dependency order:

- `constants`: where the runner's inputs live, and the tool inventories;
- `outcomes`: typed check outcomes, polarity and run stops -- the result rules' vocabulary;
- `layout`: where an iteration keeps its saved runs, how a folder's number reads back, and how a saved
  JSON file is read and written;
- `exits`: the exit codes the evals command lines share, and the parser that refuses with them;
- `specs`: the identifier shape and grader entries a scenario must satisfy, shared by the catalog
  and the conversation validator;
- `tracing`: read a stream-json trace into the facts the checks grade;
- `backing`: reviewed service containers behind a loopback audit proxy;
- `workspaces`: the fixture repository, the environment a trial sees, and what changed;
- `fingerprints`: what a result is bound to (runner source, plugin, CLI and host, case);
- `checks/`: the check registry and the checks by domain, each declared with what it asserts, what
  it reads, and whether it is a check or a probe; `checking` is the facade that keeps every name
  importable and is the module the runner calls the registry through;
- `catalog`: scenario kinds, prompts and tool grants, and validation;
- `selection`: admit finalized native case identities and retain frozen selection bytes;
- `records`: what an attempt cost, and the v1 result record;
- `invocation`: one `claude -p` call, and whether its trace may be graded;
- `rules`: the eight result rules as named functions, which grading and the attempt's life apply;
- `assessment`: a scenario's expectations in grading order, and the one grading loop the engine drives;
- `evidence`: what one attempt observed, as the evidence-v1 artifact it writes beside its grade;
- `legacy`: read a pre-evidence run directory back into evidence;
- `attempt`: one attempt's life as a state machine, written to `attempt.json` at each transition;
- `engine`: the one grading path: a live attempt's probes measured into evidence, and a scenario
  graded from an evidence record, live or saved;
- `trials`: run one trial and publish it as an attempt;
- `rescoring`: regrade, rescore and diff saved runs;
- `batches`: pool trials into a verdict per scenario;
- `cli`: the command line.

A function is patched in the module that defines it: every other module calls it through that
module (`fingerprints.plugin_provenance(...)`), so there is exactly one place it is looked up.

The evaluator's sibling modules (clean_room, graders, judge) are imported by name from evals/, the
folder that holds this package, so whatever put `probe` on the import path put them there too.
"""
