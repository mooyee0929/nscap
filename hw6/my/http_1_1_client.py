import socket
import os


class HTTPClient(): # For HTTP/1.X
    def __init__(self) -> None:
        self.sock = None

    def get(self, url, headers=None, stream=False):
        # Send the request and return the response (Object)
        # url = "http://127.0.0.1:8080/static/xxx.txt"
        # If stream=True, the response should be returned immediately after the full headers have been received.
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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        request = f"GET {path} HTTP/1.0\r\nContent-Length: 0\r\n"
        if headers:
            for key, value in headers.items():
                request += f" {key}: {value}\r\n"
        request += "\r\n"
        self.sock.send(request.encode())
        response = Response(self.sock, stream)
        print(response.headers)
        return response


class Response():
    def __init__(self, socket, stream) -> None:
        self.socket = socket
        self.stream = stream

        # fields
        self.version = "" # e.g., "HTTP/1.1"
        self.status = ""  # e.g., "200 OK"
        self.headers = {} # e.g., {content-type: application/json}
        self.body = b""  # e.g. "{'id': '123', 'key':'456'}"
        self.body_length = 0
        self.complete = False
        self.response_bytes = b""
        self.byte_sent = 0

        self.socket.settimeout(1)
        while True:
            try:
                recved = self.socket.recv(4096)
                self.response_bytes += recved
            except:
                print("timeout")
                break

        self.parse_response()

    @staticmethod
    def parse_headers(headers_str) -> dict:
        headers = {}
        for header in headers_str.split("\r\n"):
            if ":" in header:
                key, value = header.split(": ", 1)
                headers[key] = value
        return headers
 
    def parse_response(self):
        # trim GET line
        if "\r\n" in self.response_bytes.decode():
            get_line, rest = self.response_bytes.decode().split("\r\n", 1)
            self.response_bytes = rest.encode()

        # parse headers and body
        if "\r\n\r\n" in self.response_bytes.decode():
            headers_str, body = self.response_bytes.decode().split("\r\n\r\n", 1)
            self.headers = Response.parse_headers(headers_str)
            self.body = body.encode()
            self.body_length = len(self.body)

    def get_full_body(self): # used for handling short body
        if self.stream or not self.complete:
            return None
        return self.body # the full content of HTTP response body

    def get_stream_content(self): # used for receiving stream content
        if not self.stream or self.complete:
            return None
        # iteratively return the content of HTTP response body,
        # if there's still remaining content.
        # send 4096 bytes each time
        if self.byte_sent < self.body_length:
            content = self.body[self.byte_sent:self.byte_sent+4096]
            self.byte_sent += 4096
            return content
        else:
            self.complete = True
            return None


