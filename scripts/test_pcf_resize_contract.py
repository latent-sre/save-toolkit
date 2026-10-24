"""Keep unverified resize procedures out of executable PCF guidance."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalized(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


def test_pcf_resize_requires_supported_procedure_instead_of_invalid_api_payload() -> None:
    effects = normalized("skills/pcf-ops/references/state-changing-effects.md")
    assert '"options":{"memory_in_mb"' not in effects
    assert "capi-release 1.205.0+" not in effects
    assert "No supported no-downtime resize procedure is established here" in effects
    assert "target API schema" in effects
    assert "current droplet" in effects
    assert "human release owner" in effects
    assert "stops the **whole app**" in effects


def test_deploy_guide_does_not_promise_an_unverified_no_downtime_resize() -> None:
    scaling = normalized("skills/pcf-deploy/references/configuration-and-scaling.md")
    assert "For a no-downtime web resize, use the existing-droplet deployment" not in scaling
    assert "no-downtime resize requires a target-supported procedure" in scaling
    assert "`cf push -m/-k` is a new artifact" in scaling
    assert "Revision rollback does not restore scale" in scaling
