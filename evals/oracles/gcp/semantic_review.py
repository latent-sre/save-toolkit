"""Keep the free-form GCP diagnosis explicitly unmeasured by the runner.

An independent human reviews the saved response and trace under README.md. The record is
separate; neither a candidate-authored file nor a matching phrase can authorize a PASS.
"""

if __name__ == "__main__":
    print("Human review pending: assess the saved response and trace under the GCP case contract "
          "in evals/oracles/gcp/README.md.")
    raise SystemExit(2)
