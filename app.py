from flask import Flask, request, jsonify
import subprocess
import requests
import os
import time

app = Flask(__name__)

# Simulación de BD en memoria (usar una BD real en producción)
DATABASE = {
    "users": {},      # {uuid: "usuario1"}
    "requests": [],   # Lista de solicitudes con run_id y estado
}

GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

@app.route('/')
def ejecutar_ls():
    try:
        resultado = subprocess.run(['ls'], text=True, capture_output=True)
        return f"<pre>{resultado.stdout}</pre>"
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/request_anime', methods=['POST'])
def request_anime():
    data = request.json
    user_uuid = data.get("uuid")
    anime_name = data.get("animeName")
    discord_webhook = data.get("discordWebhook")
    webhook = os.getenv("WEBHOOK")
    search_type = data.get("searchType", "AllCaps")

    for req in DATABASE["requests"] :
        if req["uuid_user"] == user_uuid and req["animeName"] == anime_name and req["status"] == "in_progress":
            return jsonify({"message": "Solicitud ya en progreso", "run_id": req["run_id"]})

    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/playwright.yml/dispatches"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    payload = {
        "ref": "main",
        "inputs": {
            "uuid": user_uuid,
            "animeName": anime_name,
            "discordWebhook": discord_webhook,
            "Webhook": webhook,
            "searchType": search_type
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 204:
        return jsonify({"error": "Error al ejecutar GitHub Action", "details": response.json()}), 500

    new_request = {"uuid_user": user_uuid, "animeName": anime_name, "run_id": None, "status": "in_progress"}
    DATABASE["requests"].append(new_request)

    return jsonify({"message": "Solicitud enviada"}), 200

@app.route('/github_webhook', methods=['POST'])
def github_webhook():
    data = request.json
    uuid = data.get("uuid")
    anime_name = data.get("animeName")
    status = data.get("status")
    results = data.get("results", [])

    for req in DATABASE["requests"]:
        if req["uuid_user"] == uuid and req["animeName"] == anime_name:
            req["status"] = status
            req["results"] = results

    return jsonify({"message": "Webhook recibido y datos guardados"}), 200

@app.route('/status', methods=['GET'])
def get_status():
    user_uuid = request.args.get("uuid")

    for req in DATABASE["requests"]:
        if req["uuid_user"] == user_uuid:
            return jsonify({"status": req["status"], "run_id": req["run_id"], "results": req.get("results", [])})

    return jsonify({"error": "No hay solicitudes para este anime"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
