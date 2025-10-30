from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>سایت من روی Render</title>
</head>
<body>
  <h1>سلام — سایت من آنلاین شد ✅</h1>
  <p>این صفحه از Flask سرو می‌شود.</p>

  <h2>ارسال درخواست نمونه (POST)</h2>
  <form method="post" action="/echo">
    <input name="text" placeholder="متن را اینجا بنویس" />
    <button type="submit">ارسال</button>
  </form>

  <p>نتیجهٔ درخواست API (GET): <code>/api/ping</code></p>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)

@app.route("/echo", methods=["POST"])
def echo():
    txt = request.form.get("text", "")
    return render_template_string("""
        <p>متن فرستاده‌شده: {{txt}}</p>
        <p><a href="/">برگشت</a></p>
    """, txt=txt)

@app.route("/api/ping", methods=["GET"])
def api_ping():
    return jsonify({"status":"ok","message":"pong"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
