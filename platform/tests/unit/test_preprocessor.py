import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from genomelens.analysis.normalization.input_resolver import discover_species_from_directory
from genomelens.analysis.normalization.option_merger import (
    _align_soft,
    _cscore,
    _dbtype,
    _dist,
    _down,
    _dpi,
    _iter,
    _target_gene_ids,
    _up,
)
from genomelens.analysis.normalization.reference_resolver import _resolve_reference_index
from genomelens.analysis.normalization.request_assembler import mcscan_auto_request_from_cli
from genomelens.analysis.request_models import AnalysisSpeciesInput
from genomelens.app.controller.runners import _shared as runner_shared
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.models import GenomeInputSpec, PreparedGenomeInputSpec, RawAnnotationInputSpec
from genomelens.core.preprocessing.annotation_preprocessor import (
    CdsFeature,
    TranscriptRecord,
    has_internal_stop,
    preprocess_one,
    select_primary_transcripts,
)
from genomelens.core.validators import validate_request
from genomelens.data.workspace.output_layout import create_output_layout


def test_has_internal_stop_detects_in_frame_stop() -> None:
    assert has_internal_stop("ATGTAAATG") is True
    assert has_internal_stop("ATGAAATAA") is False
    assert has_internal_stop("ATG") is False


def test_select_primary_transcripts_prefers_longest_cds() -> None:
    genome = {"chr1": "ATG" * 100}
    t1 = TranscriptRecord(
        gene_id="G1",
        transcript_id="T1",
        seqid="chr1",
        start=1,
        end=30,
        strand="+",
        cds=[CdsFeature(seqid="chr1", start=1, end=30, strand="+")],
    )
    t2 = TranscriptRecord(
        gene_id="G1",
        transcript_id="T2",
        seqid="chr1",
        start=1,
        end=24,
        strand="+",
        cds=[CdsFeature(seqid="chr1", start=1, end=24, strand="+")],
    )
    selected = select_primary_transcripts({"T1": t1, "T2": t2}, genome)
    assert [r.transcript_id for r in selected] == ["T1"]


def test_select_primary_transcripts_prefers_no_internal_stop_on_tie() -> None:
    genome = {"chr1": "ATG" * 10 + "TAA" + "ATG" * 10}
    t1 = TranscriptRecord(
        gene_id="G1",
        transcript_id="T1",
        seqid="chr1",
        start=1,
        end=30,
        strand="+",
        cds=[CdsFeature(seqid="chr1", start=1, end=30, strand="+")],
    )
    t2 = TranscriptRecord(
        gene_id="G1",
        transcript_id="T2",
        seqid="chr1",
        start=1,
        end=30,
        strand="+",
        cds=[CdsFeature(seqid="chr1", start=32, end=61, strand="+")],
    )
    assert has_internal_stop("ATG" * 10) is False
    assert has_internal_stop("TAA" + "ATG" * 10) is True
    selected = select_primary_transcripts({"T1": t1, "T2": t2}, genome)
    assert selected[0].transcript_id == "T1"


def test_select_primary_transcripts_prefers_more_cds_fragments() -> None:
    genome = {"chr1": "ATG" * 50}
    t1 = TranscriptRecord(
        gene_id="G1",
        transcript_id="T1",
        seqid="chr1",
        start=1,
        end=30,
        strand="+",
        cds=[CdsFeature(seqid="chr1", start=1, end=30, strand="+")],
    )
    t2 = TranscriptRecord(
        gene_id="G1",
        transcript_id="T2",
        seqid="chr1",
        start=1,
        end=30,
        strand="+",
        cds=[
            CdsFeature(seqid="chr1", start=1, end=15, strand="+"),
            CdsFeature(seqid="chr1", start=16, end=30, strand="+"),
        ],
    )
    selected = select_primary_transcripts({"T1": t1, "T2": t2}, genome)
    assert selected[0].transcript_id == "T2"


def test_select_primary_transcripts_breaks_tie_by_id() -> None:
    genome = {"chr1": "ATG" * 50}
    t1 = TranscriptRecord(
        gene_id="G1",
        transcript_id="T2",
        seqid="chr1",
        start=1,
        end=30,
        strand="+",
        cds=[CdsFeature(seqid="chr1", start=1, end=30, strand="+")],
    )
    t2 = TranscriptRecord(
        gene_id="G1",
        transcript_id="T1",
        seqid="chr1",
        start=1,
        end=30,
        strand="+",
        cds=[CdsFeature(seqid="chr1", start=1, end=30, strand="+")],
    )
    selected = select_primary_transcripts({"T1": t2, "T2": t1}, genome)
    assert selected[0].transcript_id == "T1"


def test_discover_species_from_directory_recognizes_pep_input(tmp_path: Path) -> None:
    (tmp_path / "A.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (tmp_path / "A.pep").write_text(">g1\nMGV\n", encoding="utf-8")
    (tmp_path / "B.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (tmp_path / "B.pep.fa").write_text(">g1\nMGV\n", encoding="utf-8")
    species = discover_species_from_directory(tmp_path)
    names = {s.name for s in species}
    assert names == {"A", "B"}
    assert all(s.input_mode == "bed_cds" for s in species)


def test_discover_species_from_directory_allows_mixed_input_modes(tmp_path: Path) -> None:
    (tmp_path / "A.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (tmp_path / "A.cds").write_text(">g1\nATG\n", encoding="utf-8")
    (tmp_path / "B.gff3").write_text("##gff-version 3\n", encoding="utf-8")
    (tmp_path / "B.fa").write_text(">chr1\nATG\n", encoding="utf-8")

    species = discover_species_from_directory(tmp_path)

    assert [(item.name, item.input_mode) for item in species] == [("A", "bed_cds"), ("B", "gff_genome")]


def test_discover_species_from_directory_prefers_prepared_for_same_species(tmp_path: Path) -> None:
    (tmp_path / "A.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (tmp_path / "A.cds").write_text(">g1\nATG\n", encoding="utf-8")
    (tmp_path / "A.gff3").write_text("##gff-version 3\n", encoding="utf-8")
    (tmp_path / "A.fa").write_text(">chr1\nATG\n", encoding="utf-8")
    (tmp_path / "B.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (tmp_path / "B.cds").write_text(">g1\nATG\n", encoding="utf-8")

    species = discover_species_from_directory(tmp_path)

    assert [(item.name, item.input_mode) for item in species] == [("A", "bed_cds"), ("B", "bed_cds")]


def test_validate_request_accepts_mixed_input_modes(tmp_path: Path) -> None:
    query_bed = tmp_path / "query.bed"
    query_cds = tmp_path / "query.cds"
    subject_gff = tmp_path / "subject.gff3"
    subject_genome = tmp_path / "subject.fa"
    query_bed.write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    query_cds.write_text(">g1\nATG\n", encoding="utf-8")
    subject_gff.write_text("##gff-version 3\n", encoding="utf-8")
    subject_genome.write_text(">chr1\nATG\n", encoding="utf-8")

    validate_request(
        McscanRequest(
            query=GenomeInputSpec("query", prepared=PreparedGenomeInputSpec(query_bed, query_cds)),
            subject=GenomeInputSpec("subject", raw=RawAnnotationInputSpec(subject_gff, subject_genome)),
            outdir=tmp_path / "out",
        )
    )


def test_prepare_inputs_preprocesses_only_raw_side(tmp_path: Path, monkeypatch) -> None:
    query_bed = tmp_path / "query.bed"
    query_cds = tmp_path / "query.cds"
    subject_gff = tmp_path / "subject.gff3"
    subject_genome = tmp_path / "subject.fa"
    prepared_subject_bed = tmp_path / "out" / "inputs" / "prepared" / "subject.bed"
    prepared_subject_cds = tmp_path / "out" / "inputs" / "prepared" / "subject.cds"
    query_bed.write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    query_cds.write_text(">g1\nATG\n", encoding="utf-8")
    subject_gff.write_text("##gff-version 3\n", encoding="utf-8")
    subject_genome.write_text(">chr1\nATG\n", encoding="utf-8")

    calls: list[tuple[str, Path, Path, Path]] = []

    def fake_preprocess_one(name: str, gff: Path, genome: Path, outdir: Path) -> SimpleNamespace:
        calls.append((name, gff, genome, outdir))
        outdir.mkdir(parents=True, exist_ok=True)
        prepared_subject_bed.write_text("chr1\t0\t3\tg2\t0\t+\n", encoding="utf-8")
        prepared_subject_cds.write_text(">g2\nATG\n", encoding="utf-8")
        return SimpleNamespace(
            bed=prepared_subject_bed,
            cds=prepared_subject_cds,
            summary={"name": name, "input_mode": "gff_genome"},
        )

    monkeypatch.setattr(runner_shared, "preprocess_one", fake_preprocess_one)

    states: list[WorkflowState] = []
    layout = create_output_layout(tmp_path / "out", force=True)
    request = McscanRequest(
        query=GenomeInputSpec("query", prepared=PreparedGenomeInputSpec(query_bed, query_cds)),
        subject=GenomeInputSpec("subject", raw=RawAnnotationInputSpec(subject_gff, subject_genome)),
        outdir=tmp_path / "out",
    )

    query, subject, summaries = runner_shared.prepare_inputs(states.append, request, layout)

    assert query == PreparedGenomeInputSpec(query_bed, query_cds)
    assert subject == PreparedGenomeInputSpec(prepared_subject_bed, prepared_subject_cds)
    assert summaries == [{"name": "subject", "input_mode": "gff_genome"}]
    assert calls == [("subject", subject_gff, subject_genome, layout.prepared)]
    assert states == [WorkflowState.PREPROCESSING_ANNOTATIONS]
    assert layout.preprocessing_summary.is_file()


def test_request_normalizer_resolves_new_options_from_defaults() -> None:
    ns = argparse.Namespace(
        input_dir=".",
        output_dir="out",
        config="",
        jcvi_config="",
        jcvi_config_positional="",
        reference="",
        preset="auto",
        threads=None,
        min_block_size=None,
        formats="",
        force=False,
        jcvi_engine="",
        blastn="",
        makeblastdb="",
        jcvi_workflow="",
        jcvi_layout="",
        jcvi_seqids="",
        allow_simplified_fallback=False,
        align_soft="",
        dbtype="",
        cscore=None,
        dist=None,
        iter=None,
        target_genes="",
        up=None,
        down=None,
        split_targets=False,
        label_targets=False,
        glyphstyle="",
        glyphcolor="",
        shadestyle="",
        figsize="",
        dpi=None,
    )
    assert _align_soft(ns, None) == "blast"
    assert _dbtype(ns, None) == "nucl"
    assert _cscore(ns, None) == 0.7
    assert _dist(ns, None) == 20
    assert _iter(ns, None) == 1
    assert _up(ns, None) == 20
    assert _down(ns, None) == 20
    assert _dpi(ns, None) == 300


def test_request_normalizer_uses_cli_overrides() -> None:
    ns = argparse.Namespace(
        input_dir=".",
        output_dir="out",
        config="",
        jcvi_config="",
        jcvi_config_positional="",
        reference="",
        preset="auto",
        threads=None,
        min_block_size=None,
        formats="",
        force=False,
        jcvi_engine="",
        blastn="",
        makeblastdb="",
        jcvi_workflow="",
        jcvi_layout="",
        jcvi_seqids="",
        allow_simplified_fallback=False,
        align_soft="last",
        dbtype="prot",
        cscore=0.9,
        dist=50,
        iter=2,
        target_genes="AT1G01010,AT1G01020",
        up=10,
        down=15,
        split_targets=True,
        label_targets=True,
        glyphstyle="arrow",
        glyphcolor="orthogroup",
        shadestyle="curve",
        figsize="10x5",
        dpi=600,
    )
    assert _align_soft(ns, None) == "last"
    assert _dbtype(ns, None) == "prot"
    assert _cscore(ns, None) == 0.9
    assert _dist(ns, None) == 50
    assert _iter(ns, None) == 2
    assert _target_gene_ids(ns, None) == ["AT1G01010", "AT1G01020"]
    assert _up(ns, None) == 10
    assert _down(ns, None) == 15
    assert _dpi(ns, None) == 600


def test_mcscan_auto_request_from_cli_includes_local_synteny_options(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "A.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (input_dir / "A.cds").write_text(">g1\nATG\n", encoding="utf-8")
    (input_dir / "B.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (input_dir / "B.cds").write_text(">g1\nATG\n", encoding="utf-8")

    ns = argparse.Namespace(
        input_dir=str(input_dir),
        output_dir=str(tmp_path / "out"),
        config="",
        jcvi_config="",
        jcvi_config_positional="",
        reference="",
        preset="auto",
        threads=None,
        min_block_size=None,
        formats="png,pdf",
        force=True,
        jcvi_engine="",
        blastn="",
        makeblastdb="",
        jcvi_workflow="",
        jcvi_layout="",
        jcvi_seqids="",
        allow_simplified_fallback=False,
        align_soft="last",
        dbtype="nucl",
        cscore=0.8,
        dist=30,
        iter=2,
        target_genes="g1",
        up=5,
        down=5,
        split_targets=True,
        label_targets=True,
        glyphstyle="arrow",
        glyphcolor="orthogroup",
        shadestyle="curve",
        figsize="8x4",
        dpi=600,
    )
    request = mcscan_auto_request_from_cli(ns)
    method_config = request.method_config
    assert method_config["align_soft"] == "last"
    assert method_config["dbtype"] == "nucl"
    assert method_config["cscore"] == 0.8
    assert method_config["dist"] == 30
    assert method_config["iter"] == 2
    assert method_config["target_gene_ids"] == ["g1"]
    assert method_config["up"] == 5
    assert method_config["down"] == 5
    assert method_config["split_targets"] is True
    assert method_config["label_targets"] is True
    assert method_config["glyphstyle"] == "arrow"
    assert method_config["glyphcolor"] == "orthogroup"
    assert method_config["shadestyle"] == "curve"
    assert method_config["figsize"] == "8x4"
    assert method_config["dpi"] == 600
    assert request.output.formats == ["png", "pdf"]


def test_mcscan_auto_request_discovers_jcvi_config_in_input_dir(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "A.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (input_dir / "A.cds").write_text(">g1\nATG\n", encoding="utf-8")
    (input_dir / "B.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (input_dir / "B.cds").write_text(">g1\nATG\n", encoding="utf-8")
    jcvi_path = input_dir / "jcvi.config.json"
    jcvi_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "mcscan": {
                    "align_soft": "last",
                    "dbtype": "nucl",
                    "cscore": 0.9,
                },
            }
        ),
        encoding="utf-8",
    )

    ns = argparse.Namespace(
        input_dir=str(input_dir),
        output_dir=str(tmp_path / "out"),
        config="",
        jcvi_config="",
        jcvi_config_positional="",
        reference="",
        preset="auto",
        threads=None,
        min_block_size=None,
        formats="",
        force=True,
        jcvi_engine="",
        blastn="",
        makeblastdb="",
        jcvi_workflow="",
        jcvi_layout="",
        jcvi_seqids="",
        allow_simplified_fallback=False,
        align_soft="",
        dbtype="",
        cscore=None,
        dist=None,
        iter=None,
        target_genes="",
        up=None,
        down=None,
        split_targets=False,
        label_targets=False,
        glyphstyle="",
        glyphcolor="",
        shadestyle="",
        figsize="",
        dpi=None,
    )
    request = mcscan_auto_request_from_cli(ns)
    assert request.config.method_config == str(jcvi_path)
    assert request.method_config["align_soft"] == "last"
    assert request.method_config["dbtype"] == "nucl"
    assert request.method_config["cscore"] == 0.9


def test_mcscan_auto_request_falls_back_to_cwd_jcvi_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "A.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (input_dir / "A.cds").write_text(">g1\nATG\n", encoding="utf-8")
    (input_dir / "B.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (input_dir / "B.cds").write_text(">g1\nATG\n", encoding="utf-8")
    jcvi_path = tmp_path / "jcvi.config.json"
    jcvi_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "local_synteny": {
                    "dpi": 600,
                },
            }
        ),
        encoding="utf-8",
    )

    ns = argparse.Namespace(
        input_dir=str(input_dir),
        output_dir=str(tmp_path / "out"),
        config="",
        jcvi_config="",
        jcvi_config_positional="",
        reference="",
        preset="auto",
        threads=None,
        min_block_size=None,
        formats="",
        force=True,
        jcvi_engine="",
        blastn="",
        makeblastdb="",
        jcvi_workflow="",
        jcvi_layout="",
        jcvi_seqids="",
        allow_simplified_fallback=False,
        align_soft="",
        dbtype="",
        cscore=None,
        dist=None,
        iter=None,
        target_genes="",
        up=None,
        down=None,
        split_targets=False,
        label_targets=False,
        glyphstyle="",
        glyphcolor="",
        shadestyle="",
        figsize="",
        dpi=None,
    )
    request = mcscan_auto_request_from_cli(ns)
    assert request.config.method_config == str(jcvi_path)
    assert request.method_config["dpi"] == 600

    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "gff_genome_minimal"
    result = preprocess_one("query", sample / "query.gff3", sample / "query.fa", tmp_path)
    assert result.bed.is_file()
    assert result.cds.is_file()
    assert result.summary["kept_genes"] == 4


def test_resolve_reference_index_defaults_to_first() -> None:
    species = [
        AnalysisSpeciesInput(name="A", input_mode="bed_cds", bed="A.bed", cds="A.cds"),
        AnalysisSpeciesInput(name="B", input_mode="bed_cds", bed="B.bed", cds="B.cds"),
    ]
    assert _resolve_reference_index("", species) == 0


def test_resolve_reference_index_by_one_based_position() -> None:
    species = [
        AnalysisSpeciesInput(name="A", input_mode="bed_cds", bed="A.bed", cds="A.cds"),
        AnalysisSpeciesInput(name="B", input_mode="bed_cds", bed="B.bed", cds="B.cds"),
    ]
    assert _resolve_reference_index("2", species) == 1


def test_resolve_reference_index_by_name_case_insensitive() -> None:
    species = [
        AnalysisSpeciesInput(name="query", input_mode="bed_cds", bed="q.bed", cds="q.cds"),
        AnalysisSpeciesInput(name="subject", input_mode="bed_cds", bed="s.bed", cds="s.cds"),
    ]
    assert _resolve_reference_index("Subject", species) == 1


def test_mcscan_auto_request_respects_reference_species(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "A.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (input_dir / "A.cds").write_text(">g1\nATG\n", encoding="utf-8")
    (input_dir / "B.bed").write_text("chr1\t0\t3\tg1\t0\t+\n", encoding="utf-8")
    (input_dir / "B.cds").write_text(">g1\nATG\n", encoding="utf-8")

    ns = argparse.Namespace(
        input_dir=str(input_dir),
        output_dir=str(tmp_path / "out"),
        config="",
        jcvi_config="",
        jcvi_config_positional="",
        reference="B",
        preset="auto",
        threads=None,
        min_block_size=None,
        formats="",
        force=True,
        jcvi_engine="",
        blastn="",
        makeblastdb="",
        jcvi_workflow="",
        jcvi_layout="",
        jcvi_seqids="",
        allow_simplified_fallback=False,
        align_soft="",
        dbtype="",
        cscore=None,
        dist=None,
        iter=None,
        target_genes="",
        up=None,
        down=None,
        split_targets=False,
        label_targets=False,
        glyphstyle="",
        glyphcolor="",
        shadestyle="",
        figsize="",
        dpi=None,
    )
    request = mcscan_auto_request_from_cli(ns)
    assert request.input.reference_index == 1
    assert request.input.species[1].name == "B"
