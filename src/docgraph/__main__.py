"""Interfaz de línea de comandos."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from docgraph.graph import analyse


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docgraph",
        description="Analiza documentación técnica y genera un one-pager con diagrama.",
    )
    parser.add_argument(
        "--input-dir", type=Path, required=True, help="Directorio con los documentos"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("output"), help="Directorio de salida"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    load_dotenv()
    _configure_logging(args.verbose)

    result = analyse(args.input_dir, args.output_dir)

    outputs = result.get("outputs", {})
    if not outputs:
        print("No se generó ninguna salida.", file=sys.stderr)
        return 1

    print("\nGenerado:")
    for path in outputs.values():
        print(f"  {path}")

    errors = result.get("errors", [])
    if errors:
        print(f"\n{len(errors)} incidencia(s) durante el proceso:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
