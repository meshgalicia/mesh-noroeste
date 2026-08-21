"""Publicación do informe experimental Meshtastic."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from mesh_noroeste.experiment_analysis import (
    EXPERIMENT_BUCKET_SECONDS,
)
from mesh_noroeste.experiment_export import (
    write_experiment_csv,
    write_experiment_territories_csv,
    write_experiment_xlsx,
)
from mesh_noroeste.experiment_report import (
    build_experiment_report,
)
from mesh_noroeste.territory import (
    TerritoryDataError,
    TerritoryIndex,
)
from mesh_noroeste.experiment_store import (
    connect_experiment_store,
)


EXPERIMENT_PUBLIC_FILENAME = (
    "experiment.json"
)

EXPERIMENT_CSV_FILENAME = (
    "experiment.csv"
)


EXPERIMENT_TERRITORIES_CSV_FILENAME = (
    "experiment-territories.csv"
)

EXPERIMENT_XLSX_FILENAME = (
    "experiment.xlsx"
)


def _write_json_atomic(
    path: Path,
    document: Mapping[str, Any],
) -> Path:
    """Escribe JSON mediante substitución atómica."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=(
                f".{path.name}."
            ),
            suffix=".tmp",
            dir=path.parent,
        )
    )

    temporary_path = Path(
        temporary_name
    )

    os.fchmod(
        descriptor,
        0o644,
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                document,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )

            handle.write("\n")
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    except BaseException:
        try:
            temporary_path.unlink(
                missing_ok=True
            )
        finally:
            raise

    return path



def _load_experiment_territory_inputs(
    output: Path,
) -> tuple[
    Mapping[str, Any] | None,
    TerritoryIndex | None,
]:
    """Carga os datos territoriais locais se están dispoñibles.

    A ausencia ou invalidez destes ficheiros non debe impedir
    publicar o informe experimental principal.
    """

    nodes_path = (
        output
        / "nodes.json"
    )

    project_root = (
        output.parent.parent
    )

    territory_path = (
        project_root
        / "data"
        / "territory"
        / "galicia-concellos.geojson"
    )

    if (
        not nodes_path.is_file()
        or not territory_path.is_file()
    ):
        return None, None

    try:
        nodes_document = json.loads(
            nodes_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            nodes_document,
            Mapping,
        ):
            return None, None

        territory_index = (
            TerritoryIndex.from_path(
                territory_path
            )
        )

    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        TerritoryDataError,
    ):
        return None, None

    return (
        nodes_document,
        territory_index,
    )


def publish_experiment_report(
    database: Path | str,
    output_directory: Path | str,
    *,
    generated_at: str | None = None,
    start_us: int | None = None,
    end_us: int | None = None,
    bucket_seconds: int = (
        EXPERIMENT_BUCKET_SECONDS
    ),
) -> Path:
    """Publica o contrato JSON experimental.

    A base experimental segue sendo a fonte de verdade.
    O JSON público é un artefacto derivado e substituíble.
    """

    database_path = Path(
        database
    ).expanduser().resolve()

    output = Path(
        output_directory
    ).expanduser().resolve()

    (
        nodes_document,
        territory_index,
    ) = _load_experiment_territory_inputs(
        output
    )

    connection = (
        connect_experiment_store(
            database_path
        )
    )

    try:
        document = (
            build_experiment_report(
                connection,
                generated_at=generated_at,
                start_us=start_us,
                end_us=end_us,
                bucket_seconds=(
                    bucket_seconds
                ),
                nodes_document=(
                    nodes_document
                ),
                territory_index=(
                    territory_index
                ),
            )
        )

    finally:
        connection.close()

    json_path = _write_json_atomic(
        output
        / EXPERIMENT_PUBLIC_FILENAME,
        document,
    )

    write_experiment_csv(
        document,
        output
        / EXPERIMENT_CSV_FILENAME,
    )

    write_experiment_territories_csv(
        document,
        output
        / EXPERIMENT_TERRITORIES_CSV_FILENAME,
    )

    write_experiment_xlsx(
        document,
        output
        / EXPERIMENT_XLSX_FILENAME,
    )

    return json_path
