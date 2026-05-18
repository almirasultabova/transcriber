import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from transcribe import app
from flask import send_file, request, Response

PASSWORD = os.environ.get("TRANSCRIBER_PASSWORD", "sultanova")

def check_auth(password):
    return password == PASSWORD

def require_auth():
    return Response(
        'Access denied',
        401,
        {'WWW-Authenticate': 'Basic realm="Transcriber"'}
    )

def is_authenticated():
    auth = request.authorization
    return auth and check_auth(auth.password)

@app.route('/')
@app.route('/transcriber')
def index():
    if not is_authenticated():
        return require_auth()
    return send_file(os.path.join(os.path.dirname(__file__), 'index.html'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
