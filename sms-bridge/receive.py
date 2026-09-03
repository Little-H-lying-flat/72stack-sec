# -*- coding: utf-8 -*-
"""SMS 验证码桥:手机 SmsForwarder/快捷指令 POST 过来,落成 skill 可读的 latest.json
用法: python receive.py  (默认 0.0.0.0:8899,首次运行自动生成 token)
skill 读取: C:\\Users\\H\\.agents\\.sms\\latest.json  (code/ts 字段,5 分钟内有效)
"""
import json, os, re, secrets, socket, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
SMS_DIR = os.path.join(os.path.dirname(BASE), ".sms")
TOKEN_FILE = os.path.join(BASE, ".token")
LATEST = os.path.join(SMS_DIR, "latest.json")
LOG = os.path.join(SMS_DIR, "bridge.log")
PORT = 8899

os.makedirs(SMS_DIR, exist_ok=True)
if not os.path.exists(TOKEN_FILE):
    token = secrets.token_hex(8)
    open(TOKEN_FILE, "w").write(token)
    print("[*] 首次运行,token 已生成:", token, "(转发 URL 里带上它)")
TOKEN = open(TOKEN_FILE).read().strip()

def extract_code(text):
    # 常见验证码形态:4-8 位数字,取【】/「」/code: 后或独立的最后一组
    for pat in [r"[\u3010\u300c]([0-9]{4,8})[\u3011\u300d]", r"(?:code|验证码|码)[^\d]{0,4}([0-9]{4,8})",
                r"\b([0-9]{4,8})\b"]:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1)
    return ""

class H(BaseHTTPRequestHandler):
    def _save(self, text):
        code = extract_code(text)
        rec = {"code": code, "text": text[:300], "ts": int(time.time()),
               "time": time.strftime("%H:%M:%S")}
        json.dump(rec, open(LATEST, "w", encoding="utf-8"), ensure_ascii=False)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("[%s] code=%s text=%s" % (rec["time"], code or "?", text[:60]))

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/code" or parse_qs(u.query).get("token", [""])[0] != TOKEN:
            self.send_response(403); self.end_headers(); return
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", "ignore")
        text = body
        try:
            j = json.loads(body)
            text = j.get("text") or j.get("content") or j.get("sms") or body
        except Exception:
            pass
        self._save(text)
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/code" and parse_qs(u.query).get("token", [""])[0] == TOKEN:
            q = parse_qs(u.query)
            self._save(q.get("text", [""])[0])
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        elif u.path == "/ping":
            self.send_response(200); self.end_headers(); self.wfile.write(b"pong")
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    print("[*] SMS bridge 监听 0.0.0.0:%d" % PORT)
    print("[*] 手机转发 URL: http://<本机局域网IP>:%d/code?token=%s" % (PORT, TOKEN))
    print("[*] 本机局域网 IP 候选:", ip)
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
