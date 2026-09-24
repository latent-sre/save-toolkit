# PCF deployment job

For PCF deployment-job authoring. `SKILL.md` owns authority; load `stack-profile` before runner,
infrastructure, runtime or identity recommendations.

## Preconditions and design

- A self-hosted runner in an approved runner group with network access to the foundation, selected
  by that group and its labels (labels alone match any runner the repository can reach with them;
  take the group name from the runner owner, never invent one), and a pinned cf CLI v8 installation
  from an approved, checksum-verified source. The runner also supplies an approved pinned Python 3
  interpreter as `python3`; the discovery parser below uses only its standard library.
- A GitHub environment whose required reviewers and environment-scoped credentials for a
  least-privilege PCF service account are configured and available on this repository's plan.
  Naming the environment in YAML does not establish that protection.
- A deployment-branch rule on that environment limiting deploys to the reviewed branch or tags,
  verified in the repository settings. GitHub's default is no restriction, and on Free, Pro, or Team
  plans required reviewers exist only for public repositories, so without the rule and the job's
  `if:` guard a pull-request run can deploy unmerged code with production credentials.
- A trusted `build` job that uploads `app-build` with `app.zip` and a reviewed single-app
  `manifest.yml`, and exposes their SHA-256 digests as `app_sha256` and `manifest_sha256` outputs.
  The manifest must be self-contained, without credentials or a Docker-image deployment path.
- Shell tracing off. `cf auth` with no arguments reads `CF_USERNAME` and `CF_PASSWORD` from the
  environment; never put them in argv. *[sourced: cf CLI `command/v7/auth_command.go` help text]*
- Health checks, rollback commands, and the release-readiness and exact human approval evidence
  required by the existing production-change process. Preparing this evidence grants no approval.

## Planning skeleton

Follow the repository's action-version policy; absent one, pin reviewed full commit SHAs as shown.
The general skill does not impose the PCF example's identity choices on other workflows.

```yaml
deploy-prod:
  needs: build
  if: github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'  # a human starts each deploy, from main only
  runs-on: { group: <approved-pcf-runner-group>, labels: [self-hosted, pcf] }  # the group limits who may run it; labels select within it
  timeout-minutes: 20
  environment: production
  concurrency: { group: deploy-prod, cancel-in-progress: false }
  permissions: { contents: read }
  env:
    RELEASE_DIR: ${{ github.workspace }}/.pcf-release-${{ github.run_id }}-${{ github.run_attempt }}
    APP_NAME: <manifest application name>
  steps:
    - uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
      with: { name: app-build, path: '${{ env.RELEASE_DIR }}' }
    - name: Verify release bytes and cf CLI v8
      shell: bash
      env:
        APP_SHA256: ${{ needs.build.outputs.app_sha256 }}
        MANIFEST_SHA256: ${{ needs.build.outputs.manifest_sha256 }}
      run: |
        set -euo pipefail
        [[ "$APP_SHA256" =~ ^[[:xdigit:]]{64}$ && "$MANIFEST_SHA256" =~ ^[[:xdigit:]]{64}$ ]]
        printf '%s  %s\n' "$APP_SHA256" "$RELEASE_DIR/app.zip" "$MANIFEST_SHA256" "$RELEASE_DIR/manifest.yml" | sha256sum --check --status
        v="$(cf version)"; echo "$v"; [[ "$v" == *" version 8."* ]]
    - name: Deploy
      id: deploy
      shell: bash
      env:
        CF_API: ${{ secrets.CF_API }}
        CF_USERNAME: ${{ secrets.CF_USERNAME }}
        CF_PASSWORD: ${{ secrets.CF_PASSWORD }}
        CF_ORG: ${{ vars.CF_ORG }}
        CF_SPACE: ${{ vars.CF_SPACE }}
      run: |
        set -euo pipefail
        umask 077
        export CF_HOME
        CF_HOME="$(mktemp -d "${RUNNER_TEMP%/}/cf-deploy.XXXXXX")"
        trap 'rm -rf -- "$CF_HOME"' EXIT
        trap 'exit 130' INT
        trap 'exit 143' TERM
        cf api "$CF_API"
        cf auth
        cf target -o "$CF_ORG" -s "$CF_SPACE"
        # Parse complete CAPI lists, never localized `cf app` output or its failure as absence.
        read_resource() {
          python3 -I - "$1" "$2" <<'PY'
        import json, sys, uuid
        try:
            with open(sys.argv[1], encoding="utf-8") as stream:
                data = json.load(stream)
            rows, page = data["resources"], data["pagination"]
            if (type(rows) is not list or len(rows) > 1
                    or type(page["total_results"]) is not int
                    or page["total_results"] != len(rows) or page["next"] is not None):
                raise ValueError("incomplete or ambiguous list")
            if sys.argv[2] == "app":
                print(str(uuid.UUID(rows[0]["guid"])) if rows else "")
            else:
                version = rows[0]["version"]
                if type(version) is not int or version < 1 or rows[0]["deployable"] is not True:
                    raise ValueError("no usable deployed revision")
                print(version)
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise SystemExit("Discovery failed: expected a complete app list or one deployable revision")
        PY
        }
        space_guid="$(cf space "$CF_SPACE" --guid)"
        query="$(python3 -I -c 'import os,sys,uuid; from urllib.parse import urlencode; print(urlencode({"names": os.environ["APP_NAME"], "space_guids": str(uuid.UUID(sys.argv[1]))}))' "$space_guid")"
        cf curl "/v3/apps?$query" --fail > "$CF_HOME/apps.json"
        app_guid="$(read_resource "$CF_HOME/apps.json" app)"
        previous_revision=""
        first_deploy=true
        if [[ -n "$app_guid" ]]; then
          cf curl "/v3/apps/$app_guid/revisions/deployed" --fail > "$CF_HOME/revisions.json"
          previous_revision="$(read_resource "$CF_HOME/revisions.json" revision)"
          first_deploy=false
          echo "Prior deployed revision: $previous_revision"
        fi
        printf 'first_deploy=%s\nprevious_revision=%s\n' "$first_deploy" "$previous_revision" >> "$GITHUB_OUTPUT"
        cf push -f "$RELEASE_DIR/manifest.yml" -p "$RELEASE_DIR/app.zip" --strategy rolling
        cf app "$APP_NAME"
    - name: Verify health
      shell: bash
      env:
        HEALTH_URL: https://<app route>/health
      run: curl --fail --silent --show-error --max-time 10 --retry 5 --retry-delay 5 "$HEALTH_URL"
    - name: Recovery handoff
      if: ${{ (failure() || cancelled()) && steps.deploy.outcome != 'skipped' }}
      shell: bash
      env:
        FIRST_DEPLOY: ${{ steps.deploy.outputs.first_deploy }}
        PREVIOUS_REVISION: ${{ steps.deploy.outputs.previous_revision }}
      run: |
        echo "::error::Deploy or health check did not succeed. The release owner chooses the recovery:"
        if [[ "$FIRST_DEPLOY" == true ]]; then
          echo "First deploy: no previous revision exists; inspect the app and use the approved first-deploy recovery plan."
        elif [[ "$FIRST_DEPLOY" == false && "$PREVIOUS_REVISION" =~ ^[1-9][0-9]*$ ]]; then
          echo "rollout still running: cf cancel-deployment $APP_NAME"
          echo "rollout finished: cf rollback $APP_NAME --version $PREVIOUS_REVISION"
        else
          echo "Discovery incomplete or outputs unavailable: inspect the job and app state before choosing recovery."
        fi
    - name: Dispose release bytes
      if: ${{ always() }}
      shell: bash
      run: rm -rf -- "$RELEASE_DIR"
```

This is a planning example; the human release owner owns deployment execution.
`--strategy rolling` serves old and new instances at the same route during the rollout; use it only
when they are compatible. Otherwise the human release owner plans blue-green with
`/save-toolkit:pcf-deploy`. Neither path undoes data migrations or external effects.
The private `CF_HOME` contains tokens. Never cache/upload it. The runner owner must remove job
storage after forced termination or host loss, when shell traps cannot run; ephemeral registration
alone does not erase the filesystem. Record that cleanup evidence before runner reuse.

## Verification and rollback handoff

The authored job must name the post-deploy health checks and the rollback action, as the example's
discovery, `Verify health` and `Recovery handoff` steps do; it prints recovery commands and
never runs them. A successful, complete empty app list establishes a first deploy; lookup errors,
malformed responses, multiple apps, or missing/non-deployable/multiple current revisions stop
before `cf push`. First-deploy approval must include recovery without revision rollback (for example,
the release owner's approved stop/isolation of the newly created app and routes); the job never
invents a prior revision. Scope the list to the targeted space and URL-encode the name.
The [CAPI app list](https://v3-apidocs.cloudfoundry.org/version/3.219.0/index.html#list-apps) and
[deployed-revision list](https://v3-apidocs.cloudfoundry.org/version/3.219.0/index.html#list-deployed-revisions-for-an-app)
supply the machine contract; [cf CLI v8 curl](https://cli.cloudfoundry.org/en-US/v8/curl.html)
provides `--fail` for HTTP errors. This is an observation before the push, not a remote lock;
exclude concurrent deployments to this app through other jobs or humans during the approved window.
`cf rollback <app> --version <n>` requires the version and prompts unless `-f`.
`cf cancel-deployment <app>` resets the droplet but not environment-variable or binding changes, and
does not guarantee zero downtime. *[verified: cf CLI v8 source, `rollback_command.go` and
`command_list_v7.go`; Cloud Foundry rolling-deploy docs]* Revision retention limits the rollback;
see `/save-toolkit:pcf-deploy`. A job timeout or cancellation during `cf push` likely leaves the
platform rollout running, so check `cf app` before choosing. *[unverified]* Static validation
cannot prove foundation reachability, credential validity, application health, or rollback success;
keep those `[unverified]` until the human-approved run produces evidence. Report the workflow and
artifact SHA, PCF API/org/space identifiers without credentials, environment, runner group,
manifest, verification commands, rollback commands, and the approval still required.
