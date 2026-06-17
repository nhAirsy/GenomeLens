"""把 GFF/GTF 与 genome FASTA(基因组序列) 预处理为 BED 与 CDS FASTA

模块职责：
- 解析简单 GFF3/GTF annotation(注释) 与 genome FASTA(基因组序列)。
- 选择每个 gene(基因) 的主 transcript(转录本)，默认按 CDS 总长度最长。
- 写出标准 BED、CDS FASTA 与 `preprocessing_summary.json`。

失败语义：
- 输入格式缺失必要字段时抛出 `InputValidationError`。
- 无可用 CDS 时仍写 summary(摘要)，并明确 warnings(警告)。"""

# region import
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from genomelens.app.errors.exceptions import InputValidationError

# endregion


@dataclass
class CdsFeature:
    seqid: str
    start: int
    end: int
    strand: str


@dataclass
class TranscriptRecord:
    gene_id: str
    transcript_id: str
    seqid: str
    start: int
    end: int
    strand: str = "+"
    cds: list[CdsFeature] = field(default_factory=list)

    @property
    def cds_length(self) -> int:
        """返回 CDS 总长度"""

        return sum(abs(item.end - item.start) + 1 for item in self.cds)

    @property
    def span(self) -> int:
        """返回 transcript(转录本) 跨度长度"""

        return abs(self.end - self.start) + 1


@dataclass(frozen=True)
class PreprocessResult:
    """PreprocessResult(预处理结果)：一个或两个基因组的路径与摘要"""

    bed: Path
    cds: Path
    summary: dict[str, object]


def normalize_id(value: str) -> str:
    """规范化常见 gene/transcript ID(基因/转录本编号)，同时保留有用文本"""

    value = value.strip()
    value = re.sub(r"^(gene|transcript|mrna|cds)[:=]", "", value, flags=re.IGNORECASE)
    return value


def normalize_seqid(value: str) -> str:
    """规范化简单 chromosome alias(染色体别名)"""

    stripped = value.strip()
    if stripped.lower().startswith("chr"):
        suffix = stripped[3:]
        return f"chr{suffix}"
    if stripped and stripped[0].isdigit():
        return f"chr{stripped}"
    return stripped


def parse_attributes(raw: str) -> dict[str, str]:
    """把 GFF3 或 GTF 属性解析为 dict(字典)"""

    attrs: dict[str, str] = {}
    for part in raw.strip().strip(";").split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
        elif " " in part:
            key, value = part.split(" ", 1)
        else:
            continue
        # 同时兼容 GFF3 的 `key=value` 和 GTF 的 `key "value"` 风格。
        attrs[key.strip()] = value.strip().strip('"')
    return attrs


def read_fasta(path: Path) -> dict[str, str]:
    """逐行读取 FASTA，并返回按 seqid(序列编号) 索引的序列"""

    records: dict[str, list[str]] = {}
    current = ""
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                current = normalize_seqid(line[1:].split()[0])
                records.setdefault(current, [])
            elif current:
                # 先聚合分段，最后统一 join，避免长序列反复拼接。
                records[current].append(line.upper())
    return {key: "".join(value) for key, value in records.items()}


def reverse_complement(seq: str) -> str:
    """返回 DNA 序列的 reverse complement(反向互补)"""

    return seq.translate(str.maketrans("ACGTNacgtn", "TGCANtgcan"))[::-1].upper()


def parse_gff(path: Path) -> dict[str, TranscriptRecord]:
    """解析 GenomeLens 预处理所需的 GFF3/GTF 内容"""

    transcripts: dict[str, TranscriptRecord] = {}
    gene_for_transcript: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n\r")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 9:
                raise InputValidationError(f"Invalid GFF/GTF line {line_no}: expected 9 columns")
            seqid, _source, feature_type, start, end, _score, strand, _phase, attrs_raw = parts
            attrs = parse_attributes(attrs_raw)
            seqid = normalize_seqid(seqid)
            start_i = int(start)
            end_i = int(end)
            feature = feature_type.lower()
            if feature in {"gene"}:
                continue
            if feature in {"mrna", "transcript"}:
                # transcript 先建主体记录，后续 CDS 再补片段和边界。
                transcript_id = normalize_id(attrs.get("ID") or attrs.get("transcript_id") or attrs.get("Name") or "")
                gene_id = normalize_id(attrs.get("Parent") or attrs.get("gene_id") or transcript_id)
                if not transcript_id:
                    raise InputValidationError(f"Transcript without ID at line {line_no}")
                gene_for_transcript[transcript_id] = gene_id
                transcripts[transcript_id] = TranscriptRecord(
                    gene_id=gene_id,
                    transcript_id=transcript_id,
                    seqid=seqid,
                    start=start_i,
                    end=end_i,
                    strand=strand,
                )
            elif feature == "cds":
                parent_raw = attrs.get("Parent") or attrs.get("transcript_id") or attrs.get("ID")
                if not parent_raw:
                    continue
                parent = normalize_id(parent_raw.split(",")[0])
                gene_id = gene_for_transcript.get(parent, normalize_id(attrs.get("gene_id") or parent))
                # 有些注释文件会先出现 CDS，这里允许按 parent 懒创建 transcript 占位。
                record = transcripts.setdefault(
                    parent,
                    TranscriptRecord(
                        gene_id=gene_id,
                        transcript_id=parent,
                        seqid=seqid,
                        start=start_i,
                        end=end_i,
                        strand=strand,
                    ),
                )
                record.start = min(record.start, start_i)
                record.end = max(record.end, end_i)
                record.cds.append(CdsFeature(seqid=seqid, start=start_i, end=end_i, strand=strand))
    return transcripts


STOP_CODONS = {"TAA", "TAG", "TGA"}


def has_internal_stop(seq: str) -> bool:
    """检查 CDS 序列（除最后一个密码子外）是否包含终止密码子"""

    seq = seq.upper()
    if len(seq) < 3:
        return False
    # 只检查完整的三联体，忽略末尾不完整的碱基
    codons = [seq[i : i + 3] for i in range(0, len(seq) - 2, 3)]
    return any(codon in STOP_CODONS for codon in codons[:-1])


def select_primary_transcripts(
    transcripts: dict[str, TranscriptRecord],
    genome: dict[str, str],
) -> list[TranscriptRecord]:
    """按确定性规则为每个 gene(基因) 选择一个 transcript(转录本)

    选择优先级（与 JCVI One-Step SyntenyLens 保持一致）：
      1. CDS 总长度更长
      2. 无内部终止密码子
      3. CDS 片段数量更多
      4. mRNA/transcript ID 字母顺序
    """

    by_gene: dict[str, list[TranscriptRecord]] = {}
    for record in transcripts.values():
        by_gene.setdefault(record.gene_id, []).append(record)
    selected: list[TranscriptRecord] = []
    for gene_id in sorted(by_gene):
        candidates = by_gene[gene_id]
        scored = []
        for record in candidates:
            seq = extract_cds_sequence(record, genome)
            scored.append(
                (
                    # 这个排序元组就是主转录本选择策略的精确编码。
                    -record.cds_length,
                    has_internal_stop(seq),  # False（无终止）排在 True 前面
                    -len(record.cds),
                    record.transcript_id,
                    record,
                )
            )
        scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        selected.append(scored[0][4])
    return selected


def extract_cds_sequence(record: TranscriptRecord, genome: dict[str, str]) -> str:
    """为选中的 transcript(转录本) 提取 CDS 序列"""

    pieces: list[str] = []
    for cds in sorted(record.cds, key=lambda item: item.start):
        seq = genome.get(cds.seqid)
        if not seq:
            continue
        pieces.append(seq[cds.start - 1 : cds.end])
    joined = "".join(pieces)
    if record.strand == "-":
        return reverse_complement(joined)
    return joined.upper()


def preprocess_one(label: str, gff: str | Path, genome_fasta: str | Path, output_dir: str | Path) -> PreprocessResult:
    """预处理一个基因组侧并写出 BED/CDS 输出"""

    gff_path = Path(gff).expanduser().resolve(strict=False)
    genome_path = Path(genome_fasta).expanduser().resolve(strict=False)
    outdir = Path(output_dir).expanduser().resolve(strict=False)
    outdir.mkdir(parents=True, exist_ok=True)
    transcripts = parse_gff(gff_path)
    genome = read_fasta(genome_path)
    selected = select_primary_transcripts(transcripts, genome)
    bed_path = outdir / f"{label}.bed"
    cds_path = outdir / f"{label}.cds"
    warnings: list[str] = []
    bed_lines: list[str] = []
    cds_lines: list[str] = []
    kept = 0
    for record in selected:
        seq = extract_cds_sequence(record, genome)
        if not seq:
            warnings.append(f"No CDS sequence extracted for {record.transcript_id}")
            continue
        kept += 1
        # BED name 列与 CDS FASTA header 保持一致，后续 JCVI 直接用 transcript_id 对齐。
        bed_lines.append(
            "\t".join(
                [
                    record.seqid,
                    str(max(record.start - 1, 0)),
                    str(record.end),
                    record.transcript_id,
                    "0",
                    record.strand,
                ]
            )
        )
        cds_lines.append(f">{record.transcript_id}\n{seq}")
    bed_path.write_text("\n".join(bed_lines) + ("\n" if bed_lines else ""), encoding="utf-8")
    cds_path.write_text("\n".join(cds_lines) + ("\n" if cds_lines else ""), encoding="utf-8")
    summary = {
        "label": label,
        "input_mode": "gff_genome",
        "gff": str(gff_path),
        "genome": str(genome_path),
        "parsed_transcripts": len(transcripts),
        "selected_transcripts": len(selected),
        "kept_genes": kept,
        "bed": str(bed_path),
        "cds": str(cds_path),
        "selection_strategy": "longest_cds_no_internal_stop_most_cds_fragments_then_id",
        "warnings": warnings,
    }
    # 这份 summary 会被 shell summary 和 GUI 直接引用，所以尽量保留足够的输入上下文。
    return PreprocessResult(bed=bed_path, cds=cds_path, summary=summary)


def write_preprocessing_summary(path: str | Path, summaries: list[dict[str, object]]) -> Path:
    """写出公开的 `preprocessing_summary.json`"""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # 无论 pairwise 还是多物种流程，都统一走同一个 preprocessing_summary 协议。
    payload = {"input_mode": "gff_genome", "genomes": summaries}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
