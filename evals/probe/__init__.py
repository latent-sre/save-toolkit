"""The eval runner behind `evals/build_probe.py`, one module per job, in dependency order:

- `constants`: where the runner's inputs live, and the tool inventories;
- `outcomes`: typed check outcomes, polarity and run stops -- the result rules' vocabulary;
- `tracing`: read a stream-json trace into the facts the checks grade;
- `backing`: reviewed service containers behind a loopback audit proxy;
- `workspaces`: the fixture repository, the environment a trial sees, and what changed;
- `fingerprints`: what a result is bound to (runner source, plugin, CLI and host, case);
- `checking`: the checks, each declared with what it asserts and what it reads;
- `catalog`: scenario kinds, prompts and tool grants, and validation;
- `records`: what an attempt cost, and the v1 result record;
- `invocation`: one `claude -p` call, and whether its trace may be graded;
- `assessment`: the one grading loop, shared by live grades and regrades;
- `trials`: run one trial and publish it as an attempt;
- `rescoring`: regrade, rescore and diff saved runs;
- `batches`: pool trials into a verdict per scenario;
- `cli`: the command line.

A function is patched in the module that defines it: every other module calls it through that
module (`fingerprints.plugin_provenance(...)`), so there is exactly one place it is looked up.

The evaluator's sibling modules (clean_room, graders, judge) are imported by name from evals/, the
folder that holds this package, so whatever put `probe` on the import path put them there too.
"""
