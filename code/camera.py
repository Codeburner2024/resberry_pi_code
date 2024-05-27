import io
import logging
import socketserver
from http import server
from threading import Condition

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

import base64

#USERNAME = "your_ID" #라즈베리파이 계정 아이디
#PASSWORD = "your_PW" #라즈베리파이 비밀번호

# 사용자 인증 수행하는 함수
#def check_auth(headers):
#    auth = headers.get('Authorization')
#    if not auth:
#        return False
#    token = auth.split()[1]
#    given_user, given_pass = base64.b64decode(token).decode('utf-8').split(':')
#    return given_user == USERNAME and given_pass == PASSWORD


PAGE = """\
<html>
<head>
<title>picamera2 demo</title>
</head>
<body>
<img src="stream.mjpg" width="555" height="210" />
</body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
#        if not check_auth(self.headers):
#            self.send_response(401)
#            self.send_header('WWW-Authenticate', 'Basic realm=\"Authentication required\"')
#            self.end_headers()
#            self.wfile.write('Authentication failed'.encode('utf-8'))
#            return

        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (555, 210)}))
output = StreamingOutput()
picam2.start_recording(MJPEGEncoder(), FileOutput(output))

try:
    address = ('IP주소', 8000) # IP주소 부분은 라즈베리파이 ifconfig를 통해서 찾아서 작성
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    picam2.stop_recording()
