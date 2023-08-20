import struct
import socket
import threading
import time
from collections import deque


# define format of HTTP 2 frame format
class Frame:
    def __init__(self):
        self.length: int = 0
        self.type: int = 0
        self.flags: int = 0
        self.stream_id: int = 0
        self.payload: bytes = b""

    def pack_frame(type: int, flags: int, stream_id: int, payload: bytes):
        length = len(payload)
        pack_str = f"!3sBBI{length}s"
        return struct.pack(pack_str, length.to_bytes(3, 'big'), type, flags, stream_id, payload)


    def unpack_frame(self, frame_header: bytes):
        self.length, self.type, self.flags, self.stream_id = struct.unpack("!3sBBI", frame_header)
        self.length = int.from_bytes(self.length, 'big')

class Request:
    def __init__(self, method, path, headers=None, body=None):
        self.method = "GET"
        self.path = path
        self.headers = headers if headers is not None else {}
        self.body = body

    def to_frame(self, stream_id):
        if self.headers is None:
            return Frame.pack_frame(1, 1, stream_id, "")
        header_string = ""
        for key, value in self.headers.items():
            header_string += f"{key}: {value}\r\n"
        payload = f"{self.method} {self.path} HTTP/2.0\r\n{header_string}\r\n".encode("utf-8")
        return Frame.pack_frame(1, 1, stream_id, payload)

class Response():
    def __init__(self, stream_id, headers = {}, status = "Not yet") -> None:
        self.stream_id = stream_id
        self.headers = headers
        
        self.status = status
        self.body = b""

        self.contents = deque()
        self.complete = False

    def get_headers(self):
        begin_time = time.time()
        while self.status == "Not yet":
            if time.time() - begin_time > 5:
                return None
        return self.headers
    
    def get_full_body(self): # used for handling short body
        begin_time = time.time()
        while not self.complete:
            if time.time() - begin_time > 5:
                return None
        if len(self.body) > 0:
            return self.body
        while len(self.contents) > 0:
            self.body += self.contents.popleft()
        return self.body # the full content of HTTP response body

    def get_stream_content(self): # used for handling long body
        begin_time = time.time()
        while len(self.contents) == 0: # contents is a buffer, busy waiting for new content
          if self.complete or time.time()-begin_time > 5: # if response is complete or timeout
              return None
        content = self.contents.popleft() # pop content from deque
        return content # the part content of the HTTP response body


class HTTPClient(): # For HTTP/2.X
    def __init__(self) -> None:
        self.sock = None
        self.last_stream_id = -1
        self.streams = {}
        self.recv_thread = threading.Thread(target=self.recv_worker)
        self.recv_thread.start()

    def form_request_frame(self, path, headers=None, body=None, stream_id=0) -> bytes:
        headers = {
            "method": "GET",
            "path": path,
            "scheme": "http",
            "authority": "127.0.0.1:8080",
            "Content-Length": "0"
        }
        request = Request("GET", path, headers, body)

        return request.to_frame(stream_id)

    def recv_worker(self):
        while self.sock is None:
            time.sleep(0.1)

        while True:
            # get frame header
            try:
                frame_header = self.sock.recv(9)
            except:
                continue
            frame = Frame()
            frame.unpack_frame(frame_header)
            # read frame payload
            frame.payload = self.sock.recv(frame.length)

            if frame.stream_id not in self.streams:
                self.streams[frame.stream_id] = Response(frame.stream_id)
            if frame.type == 0x1: # headers frame
                headers = {}
                header = frame.payload.decode("utf-8")
                for line in header.split("\r\n"):
                    if ":" in line:
                        key, value = line.split(": ", 1)
                        headers[key] = value
                self.streams[frame.stream_id].headers = headers
            if frame.type == 0x0: # data frame
                self.streams[frame.stream_id].contents.append(frame.payload)

            if frame.flags == 0x1 and frame.type == 0x0: # end of stream and data frame
                self.streams[frame.stream_id].complete = True
                self.streams[frame.stream_id].status = "Complete"


    def get(self, url, headers=None, stream=False):
        if url.startswith("http://"):
            url = url.replace("http://","")
        para = url.split("/")
        host_list = para[0]
        host_parts = host_list.split(":")
        host = host_parts[0]
        if len(host_parts) > 1:
            port = int(host_parts[1])  # The second part is the port number
        else:
            port = 8080  # Default port is 80 for HTTP
        # Join the remaining parts as the path
        path = "/"+ "/".join(para[1:])
        print(host,port,path)
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            # set socket to be non blocking
            self.sock.setblocking(False)

        # Send the request and return the response
        self.last_stream_id += 2
        self.sock.send(self.form_request_frame(path, headers=headers, stream_id=self.last_stream_id))
        self.streams[self.last_stream_id] = Response(self.last_stream_id)

        return self.streams[self.last_stream_id]
