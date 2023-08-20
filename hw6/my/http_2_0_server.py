import socket
import threading
import os
import struct
import random


class Frame():
    def __init__(self) -> None:
        self.length = 0
        self.type = 0
        self.flag = 0
        self.stream_id = 0
        self.payload = b""

    def pack_frame(type,flag,stream_id,payload):
        length = len(payload)
        pack_str = f"!3sBBI{length}s"
        return struct.pack(pack_str, length.to_bytes(3, 'big'), type, flag, stream_id, payload)

    def unpack_frame(self, frame_header):
        self.length, self.type, self.flag, self.stream_id = struct.unpack("!3sBBI", frame_header)
        self.length = int.from_bytes(self.length, 'big')


class HTTPServer:
    def __init__(self, host="127.0.0.1", port=8080):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.static_path = ""

    def run(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"Server listening on {self.host}:{self.port}")
        while True:
            client_socket, address = self.server_socket.accept()
            # create a thread to handle the request
            th = threading.Thread(target=self.handle_request, args=[client_socket])
            th.start()

    def handle_request(self, client_socket):
        while True:
            request_frame = client_socket.recv(9)
            
            if not request_frame:
                continue
            request = Frame()
            request.unpack_frame(request_frame)
            
            request.payload = client_socket.recv(request.length)

            # parse request
            request.payload = request.payload.decode("utf-8")
            print("recv stream__id:",request.stream_id,"type",request.type)
            method, resource, http_version = request.payload.split("\r\n", 1)[0].split(" ")
            headers_list = request.payload.split("\r\n")[1:]
            headers = dict()
            for header in headers_list:
                if header:
                    key, value = header.split(": ", 1)
                    headers[key] = value
            # handle request
            if resource == "/":
                file_list = os.listdir(self.static_path)
                file_list = random.sample(file_list,k=3)
                data = "<html><header></header><body>"
                for file in file_list:
                    data += f'<a href="/static/{file}">{file}</a><br/>'
                # if body end with <br>, remove it
                if data.endswith("<br/>"):
                    data = data[:-5]
                data += "</body></html>"
                data_frame = Frame.pack_frame(0x0, 0x1, request.stream_id, data.encode("utf-8"))
                headers = {
                    "content-type": "text/html",
                    "Content-Length": str(len(data))
                }
                if headers is None:
                    headers = dict()
                response = "HTTP/2.0 200 OK\r\n"
                for key, value in headers.items():
                    response += f"{key}: {value}\r\n"
                response += "\r\n"
                header_frame = Frame.pack_frame(0x1, 0x1, request.stream_id, response.encode("utf-8"))

                # send frames
                client_socket.send(header_frame)
                client_socket.send(data_frame)
            elif resource.startswith("/static"):
                # get file path
                file_path = self.static_path + resource[7:]
                # get file frame list
                file_frame_list = self.get_file_frame_list(file_path, request.stream_id, client_socket)
                # get header frame
                headers = {
                    "content-type": "application/octet-stream",
                    "Content-Length": str(os.path.getsize(file_path))
                }
                if headers is None:
                    headers = dict()
                response = "HTTP/2.0 200 OK\r\n"
                for key, value in headers.items():
                    response += f"{key}: {value}\r\n"
                response += "\r\n"
                header_frame = Frame.pack_frame(0x1, 0x1, request.stream_id, response.encode())
                # send frames
                client_socket.send(header_frame)
                for frame in file_frame_list:
                    client_socket.send(frame)


    def get_file_frame_list(self, file_path, stream_id, client_socket) -> list:
        with open(file_path, "rb") as file:
            file_content = file.read()
        file_length = len(file_content)
        frame_list = []
        for i in range(0, file_length, 4096):
            frame = Frame.pack_frame(0x0, 0x0, stream_id, file_content[i:i+4096])
            frame_list.append(frame)
        # modify last frame's flag
        frame_list[-1] = Frame.pack_frame(0x0, 0x1, stream_id, file_content[i:i+4096])
        return frame_list


    def set_static(self, path):
        self.static_path = path

    def close(self):
        self.server_socket.close()
