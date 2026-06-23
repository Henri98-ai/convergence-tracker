"""
Serveur proxy pour Convergence Tracker
Déploiement : Render.com ou local
"""

import http.server
import urllib.request
import urllib.parse
import json
import os
import datetime

PORT = int(os.environ.get("PORT", 5000))
APP_PASSWORD = os.environ.get("APP_PASSWORD", "Isagri2026")

class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  → {args[0]} {args[1]}")

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-App-Password")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Route : / → page principale
        if parsed.path in ["/", "/index.html"]:
            index_path = os.path.join(os.path.dirname(__file__), "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
            return

        # Vérifier le mot de passe depuis header OU paramètre URL
        params_all = urllib.parse.parse_qs(parsed.query)
        app_pwd = self.headers.get("X-App-Password", "") or params_all.get("pwd", [""])[0]
        if app_pwd != APP_PASSWORD:
            self.send_response(401)
            self.send_cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Mot de passe incorrect"}).encode())
            return

        # Route : /jira → proxy vers Jira
        if parsed.path == "/jira":
            jira_path = params.get("path", [""])[0]
            jira_query = params.get("query", [""])[0]
            auth = self.headers.get("Authorization", "")

            # Logger la connexion (email extrait du Basic Auth)
            try:
                import base64
                decoded = base64.b64decode(auth.replace("Basic ", "")).decode()
                email = decoded.split(":")[0]
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                # Logger uniquement les appels sprint (pas tous les changelogs)
                if "board" in jira_path and "sprint" in jira_path and "issue" not in jira_path:
                    print(f"  📊 CONNEXION — {email} — {now}")
            except:
                pass

            if not jira_path or not auth:
                self.send_response(400)
                self.end_headers()
                return

            url = f"https://isagri.atlassian.net{jira_path}"
            if jira_query:
                url += "?" + jira_query

            req = urllib.request.Request(url)
            req.add_header("Authorization", auth)
            req.add_header("Accept", "application/json")

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                self.send_response(200)
                self.send_cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                self.send_cors()
                self.end_headers()
                self.wfile.write(str(e).encode())
            except Exception as e:
                self.send_response(500)
                self.send_cors()
                self.end_headers()
                self.wfile.write(str(e).encode())
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    print("=" * 50)
    print("  Convergence Tracker — Serveur")
    print("=" * 50)
    print(f"\n  ✅ Port : {PORT}")
    print(f"  🔒 Mot de passe : {APP_PASSWORD}")
    print(f"\n  (Ctrl+C pour arrêter)\n")

    server = http.server.HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  Serveur arrêté.")
