import os
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = None  # без лимита на размер файла

DEEPGRAM_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
PASSWORD = os.environ.get("TRANSCRIBER_PASSWORD", "sultanova")


def _authenticated():
    auth = request.authorization
    return auth and auth.password == PASSWORD


@app.route("/api/transcribe", methods=["POST", "OPTIONS"])
def transcribe():
    if request.method != "OPTIONS" and not _authenticated():
        return Response('Access denied', 401, {'WWW-Authenticate': 'Basic realm="Transcriber"'})
    if request.method == "OPTIONS":
        resp = jsonify({})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    if "file" not in request.files:
        return jsonify({"error": "Файл не найден"}), 400

    file = request.files["file"]
    ext = os.path.splitext(file.filename)[1].lower()

    allowed = {".mp3", ".m4a", ".wav", ".ogg", ".webm", ".mp4", ".mov"}
    if ext not in allowed:
        return jsonify({"error": f"Формат {ext} не поддерживается"}), 400

    mime_map = {
        ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav",
        ".ogg": "audio/ogg", ".webm": "audio/webm",
        ".mp4": "video/mp4", ".mov": "video/quicktime",
    }
    content_type = mime_map.get(ext, "application/octet-stream")

    try:
        audio_data = file.read()

        resp = requests.post(
            "https://api.deepgram.com/v1/listen?model=nova-2&language=ru&smart_format=true&punctuate=true&paragraphs=true",
            headers={
                "Authorization": f"Token {DEEPGRAM_KEY}",
                "Content-Type": content_type,
            },
            data=audio_data,
            timeout=600,
        )
        resp.raise_for_status()
        data = resp.json()

        channels = data.get("results", {}).get("channels", [])
        if not channels:
            return jsonify({"error": "Deepgram не вернул результатов"}), 400

        alt = channels[0].get("alternatives", [{}])[0]
        text = alt.get("transcript", "").strip()

        if not text:
            return jsonify({"error": "Текст не распознан — нет речи в записи"}), 400

        paragraphs_data = alt.get("paragraphs", {}).get("paragraphs", [])
        if paragraphs_data:
            parts = [" ".join(s["text"] for s in p.get("sentences", [])) for p in paragraphs_data]
            formatted = "\n\n".join(p for p in parts if p)
        else:
            formatted = text

        response = jsonify({"text": formatted, "raw": text, "filename": file.filename})
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500
