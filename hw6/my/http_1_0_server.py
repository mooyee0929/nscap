import socket
import json
import threading
import os
import json

class HTTPServer():
    def __init__(self, host="127.0.0.1", port=8080) -> None:
        self.host = host
        self.port = port
        # Create a socket object
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind the socket to a specific address and port
        self.socket.bind((host, port))
        
        # Listen for incoming connections
        self.socket.listen(1)
        self.static_path = ""
        # Create a thread to accept clients


    def run(self):
        # Create the server socket and start accepting connections.
        print(f"Server listening on {self.host}:{self.port}")
        while True:
            client_socket, address = self.socket.accept()
            # handle the request
            self.handle_request(client_socket)

    def handle_request(self, client_socket):
        request = {
        'method': "", # e.g. "GET"
        'path': "", # e.g. "/"
        'params': {}, # e.g. {'id': '123'}
        'version': "", # e.g. "HTTP/1.0"
        'headers': {}, # e.g. {content-type: application/json}
        'body': ""  # e.g. "{'id': '123', 'key':'456'}"
        }

        response = {
        'path': "", # e.g. "/"
        'version': "", # e.g. "HTTP/1.0"
        'headers': {}, # e.g. {content-type: application/json}
        'body': ""  # e.g. "{'id': '123', 'key':'456'}"
        }
        request_str = client_socket.recv(4096).decode()
        lines = request_str.split('\r\n',1)
        request_list = lines[0].split(" ")
        print(request_str)
        request['method'] = request_list[0]
        resource = request_list[1]
        request['version'] = request_list[2]

        if resource == "/":
            file_list = os.listdir(self.static_path)
            body = "<html><header></header><body>"
            for file in file_list:
                body += f'<a href="/static/{file}">{file}</a><br/>'
            # if body end with <br>, remove it
            if body.endswith("<br/>"):
                body = body[:-5]
            body += "</body></html>"
            response["headers"]["Content-Length"] = len(body)
            response["headers"]["Content-Type"] = "text/html"
            response_str = f"HTTP/1.0 '200 OK'\r\n"
            if response["headers"]:
                for key, value in  response["headers"].items():
                    response_str += f"{key}: {value}\r\n"
            response_str += "\r\n"
            response_str += body
        else:
            file_path = self.static_path + resource[len("/static"):]
            print(file_path)
            if os.path.isfile(file_path):
                with open(file_path, "rb") as file:
                    file_content = file.read().decode()
                response["headers"]["Content-Length"] = len(file_content)
                response["headers"]["Content-Type"] = "application/octet-stream"
                response_str = f"HTTP/1.0 '200 OK'\r\n"
                if response["headers"]:
                    for key, value in  response["headers"].items():
                        response_str += f"{key}: {value}\r\n"
                response_str += "\r\n"
                if file_content:
                    response_str += file_content

            else:
                response_str = f"HTTP/1.0 404 NOT Found"
        client_socket.send(response_str.encode())
        

    def set_static(self, path):
        # Set the static directory so that when the client sends a GET request to the resource "/static/<file_name>", the file located in the static directory is sent back in the response.
        self.static_path = path
    
    def close(self):
        # Close the server socket.
        self.server_socket.close()