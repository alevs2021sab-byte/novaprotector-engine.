
import json
import os
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BYTES = 200_000
PORT = int(os.environ.get("PORT", "10000"))
API_KEY = os.environ.get("ENGINE_API_KEY", "")


def respond(handler, status, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.path != "/health":
            respond(self, 404, {
                "success": False,
                "error": "Ruta no encontrada"
            })
            return

        respond(self, 200, {
            "success": True,
            "service": "NovaProtector Engine",
            "parser": "Luau",
            "mode": "validation-only"
        })

    def do_POST(self):
        if self.path != "/validate":
            respond(self, 404, {
                "success": False,
                "error": "Ruta no encontrada"
            })
            return

        if not API_KEY:
            respond(self, 503, {
                "success": False,
                "error": "El servicio aún no está configurado"
            })
            return

        if self.headers.get("Authorization", "") != "Bearer " + API_KEY:
            respond(self, 401, {
                "success": False,
                "error": "No autorizado"
            })
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        if length <= 0:
            respond(self, 400, {
                "success": False,
                "error": "La solicitud está vacía"
            })
            return

        if length > MAX_BYTES:
            respond(self, 413, {
                "success": False,
                "error": "El límite es de 200 KB"
            })
            return

        try:
            payload = json.loads(
                self.rfile.read(length).decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            respond(self, 400, {
                "success": False,
                "error": "JSON inválido"
            })
            return

        if not isinstance(payload, dict):
            respond(self, 400, {
                "success": False,
                "error": "Se esperaba un objeto JSON"
            })
            return

        source = payload.get("code")

        if not isinstance(source, str) or not source.strip():
            respond(self, 400, {
                "success": False,
                "error": "Introduce código Luau"
            })
            return

        if len(source.encode("utf-8")) > MAX_BYTES:
            respond(self, 413, {
                "success": False,
                "error": "El código supera los 200 KB"
            })
            return

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".luau"
            ) as file:
                file.write(source)
                file.flush()

                result = subprocess.run(
                    [
                        "/usr/local/bin/luau-compile",
                        "--only-parse",
                        file.name
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False
                )

            if result.returncode != 0:
                respond(self, 422, {
                    "success": False,
                    "valid": False,
                    "error": (result.stderr or result.stdout).strip()[:2000]
                })
                return

            respond(self, 200, {
                "success": True,
                "valid": True,
                "mode": "validation-only",
                "message": "El código pasó el análisis sintáctico."
            })

        except subprocess.TimeoutExpired:
            respond(self, 408, {
                "success": False,
                "error": "Se agotó el tiempo de análisis"
            })
        except Exception:
            respond(self, 500, {
                "success": False,
                "error": "Error interno del motor"
            })


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
  
