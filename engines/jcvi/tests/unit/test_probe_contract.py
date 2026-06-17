from jcvi_genomelens.probe import build_probe_payload
from jcvi_genomelens.workflow_contract import SUPPORTED_WORKFLOWS


def test_probe_contract() -> None:
    payload = build_probe_payload()
    assert payload["engine_name"] == "jcvi-genomelens"
    assert payload["status"] == "ok"
    assert payload["runtime_mode"] in {"core", "accelerated"}
    assert isinstance(payload["loaded_extensions"], list)
    assert isinstance(payload["missing_extensions"], list)
    assert isinstance(payload["extension_errors"], dict)
    assert payload["capabilities"] == list(SUPPORTED_WORKFLOWS)
    assert payload["capabilities"] == [
        "mcscan_pairwise",
        "graphics_synteny",
        "graphics_dotplot",
        "graphics_karyotype",
        "catalog_ortholog",
        "local_synteny",
        "graphics_karyotype_global",
    ]
    assert payload["dispatchable_workflows"] == payload["capabilities"]
    assert "jcvi.graphics.dotplot" in payload["bundled_jcvi_modules"]
    assert "jcvi.graphics.karyotype" in payload["bundled_jcvi_modules"]
