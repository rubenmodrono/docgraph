"""Comprobación manual del servidor MCP sobre stdio.

No es un test de pytest: arranca el servidor como subproceso y hace un
handshake JSON-RPC real, que es la única forma de saber que el transporte
funciona de extremo a extremo.

Mantiene stdin abierto hasta recibir cada respuesta. Cerrarlo antes hace que
el servidor empiece a apagarse y la respuesta pendiente nunca se emita.

    python tests/manual_mcp_handshake.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

TIMEOUT_S = 120


def send(proc: subprocess.Popen, method: str, params=None, id_=None) -> None:
    msg: dict = {"jsonrpc": "2.0", "method": method}
    if id_ is not None:
        msg["id"] = id_
    if params is not None:
        msg["params"] = params
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def await_id(proc: subprocess.Popen, id_: int) -> dict:
    """Lee líneas hasta encontrar la respuesta a `id_`."""
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError(f"el servidor cerró stdout sin responder a id={id_}")
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == id_:
            return msg


def main() -> int:
    env = {**os.environ}
    env.pop("GEMINI_API_KEY", None)  # sin gasto: modo offline

    proc = subprocess.Popen(
        [sys.executable, "-m", "docgraph.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
        bufsize=1,
    )

    try:
        send(
            proc,
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "handshake", "version": "1.0"},
            },
            id_=1,
        )
        init = await_id(proc, 1)["result"]
        print(f"  initialize  -> {init['serverInfo']['name']} "
              f"(protocolo {init['protocolVersion']})")

        send(proc, "notifications/initialized")

        send(proc, "tools/list", {}, id_=2)
        for tool in await_id(proc, 2)["result"]["tools"]:
            print(f"  tools/list  -> {tool['name']}: {tool.get('title', '')}")

        send(
            proc,
            "tools/call",
            {
                "name": "analyse_text",
                "arguments": {"text": "# Servicio\n\nPublica eventos en una cola."},
            },
            id_=3,
        )
        call = await_id(proc, 3)
        if "error" in call:
            print(f"  tools/call  -> ERROR: {call['error']}")
            return 1

        contenido = call["result"].get("structuredContent", {})
        print(f"  tools/call  -> ok, claves: {sorted(contenido)}")

        send(
            proc,
            "tools/call",
            {"name": "analyse_text", "arguments": {"text": "   "}},
            id_=4,
        )
        vacio = call = await_id(proc, 4)
        fallo = vacio["result"].get("isError") or "error" in vacio
        print(f"  texto vacío -> rechazado correctamente: {bool(fallo)}")
        if not fallo:
            return 1

        return 0
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
