"""One command from ledger to every published artefact."""

import json
from pathlib import Path

from . import charts, generator, report, validation, variance
from .model import Ledger

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MONTH = "2026-06"


def run(month: str = DEFAULT_MONTH, root: Path | None = None) -> dict:
    root = Path(root) if root is not None else ROOT

    raw = generator.build_ledger()
    data_path = root / "data" / "ledger.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(raw, indent=1) + "\n", encoding="utf-8")

    ledger = Ledger.from_dict(raw)
    analysis = variance.analyse_month(ledger, month)
    key = report.build_answer_key(ledger, month)
    checks = validation.run_checks(ledger, analysis, key)

    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    report.write_json(key, outputs / "answer_key.json")
    (outputs / "answer_key.md").write_text(
        report.render_answer_key_md(key), encoding="utf-8"
    )
    (outputs / "MONTHLY_PACK.md").write_text(
        report.render_pack(analysis, key), encoding="utf-8"
    )
    (outputs / "validation_report.md").write_text(
        validation.render_report(checks), encoding="utf-8"
    )

    report.write_tables(analysis, outputs / "tables")

    charts.bridge_waterfall(analysis, outputs / "charts" / "01_bridge_waterfall.png")
    charts.gross_profit_trend(
        analysis, variance.trend(ledger), outputs / "charts" / "02_gross_profit_trend.png"
    )
    charts.variance_by_owner(analysis, outputs / "charts" / "03_variance_by_owner.png")

    return {
        "month": month,
        "fingerprint": ledger.fingerprint,
        "all_passed": validation.all_passed(checks),
        "checks": len(checks),
        "exceptions": len(analysis.exceptions),
        "gross_profit_variance": str(analysis.gross_profit_variance),
    }
