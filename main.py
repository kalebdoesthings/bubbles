import threading
from flask import Flask, render_template, request, jsonify
from torrentDownload import addTorrent, progress

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/downloading")
def downloading():
    # single-page app now lives in index.html; it reads the view from the hash
    return render_template("index.html")


@app.route("/progress")
def get_progress():
    return jsonify(progress)


@app.route("/addMagnet", methods=["POST"])
def addMagnet():
    data = request.get_json()
    magnet = data.get("magnet")
    if not magnet:
        return jsonify({"error": "no magnet provided"}), 400

  
    threading.Thread(target=addTorrent, args=([magnet],), daemon=True).start()

    return jsonify({"status": "started", "magnet": magnet})





if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
