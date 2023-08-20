import os
import threading
import time
import random
from QUIC import quic_server as qs

class Client_Handler:
    def __init__(self, socket :qs.QUICServer, address, static_path):
        self.socket = socket
        self.address = address
        self.static_path = static_path
        self.alive = True

        self.recv_thread =  threading.Thread(target=self.recv)
        self.recv_thread.start()

        self.request_handle_thread_list = []

    def recv(self):
        while self.alive:
            try:
                stream_id, frame, flag = self.socket.recv()
                print(f'RECV # stream_id: {stream_id} flag: {flag}')
                request_handle_thread = threading.Thread(target=self.request_handle, args=(stream_id, frame))
                self.request_handle_thread_list.append(request_handle_thread)
                request_handle_thread.start()
            except:
                self.alive = False
                self.socket.close()
                break
    
    def request_handle(self, stream_id, frame):
        frame_type = frame[0]
        length = int.from_bytes(frame[1:5], byteorder='big')
        payload = frame[5:].decode('utf-8')

        # data frame
        if frame_type == 0:
            pass
        # hdr frame
        elif frame_type == 1:
            item_list = payload.split('\r\n')
            payload_dict = {key: val for item in item_list for key, val in [item.split(': ')]}
            header_dict = payload_dict
            if header_dict['method'] == 'GET':
                path = header_dict['path']
                if path == '/':
                    # hdr frame
                    payload = f'status: 200 OK\r\ncontent-type: text/html'.encode('utf-8')
                    frame_type, length = self.make_header('hdr_frame', payload)
                    frame = frame_type + length + payload
                    self.send(stream_id, frame, False)

                    #data frame
                    files = os.listdir(self.static_path)
                    three_random_files = random.sample(files, 3)
                    payload_ = '<html><header></header><body>'
                    for i, file in enumerate(three_random_files):
                        link = f'<a href="/static/{file}">{file}</a>'
                        if i != 2:
                            link+='<br/>'
                        payload_ += link
                    payload_ += '</body></html>'
                    payload = payload_.encode('utf-8')
                    frame_type, length = self.make_header('data_frame', payload)
                    frame = frame_type + length + payload
                    self.send(stream_id, frame, True)

                elif self.static_path and path.startswith('/static/'):
                    file = os.path.join(self.static_path, path[8:])
                    if os.path.exists(file):
                        with open(file, 'rb') as f:
                            content = f.read()
                            # hdr frame
                            payload = f'status: 200 OK\r\ncontent-type: text/plain'.encode('utf-8')
                            frame_type, length = self.make_header('hdr_frame', payload)
                            frame = frame_type + length + payload
                            self.send(stream_id, frame, False)

                            # data frame
                            payload = content
                            frame_type, length = self.make_header('data_frame', payload)
                            frame = frame_type + length + payload
                            self.send(stream_id, frame, True)

                    else:
                        error_message = '404 Not Found'
                        payload = error_message.encode('utf-8')
                        frame_type, length = self.make_header('hdr_frame', payload)
                        frame = frame_type + length + payload
                        self.send(stream_id, frame, True)
                else:
                    error_message = '400 Bad Request'
                    payload = error_message.encode('utf-8')
                    frame_type, length = self.make_header('hdr_frame', payload)
                    frame = frame_type + length + payload
                    self.send(stream_id, frame, True)
            else:
                error_message = '501 Not Implemented'
                payload = error_message.encode('utf-8')
                frame_type, length = self.make_header('hdr_frame', payload)
                frame = frame_type + length + payload
                self.send(stream_id, frame, True)

    def send(self, stream_id, frame, flag):
        # print(f'SEND # stream_id: {stream_id} flag: {flag}')
        # print(f'frame: {frame}\n')
        self.socket.send(stream_id, frame, flag)



    def make_header(self, frame_type_, payload_):
        type_dict = {
            'data_frame':int(0).to_bytes(1, byteorder='big'),
            'hdr_frame':int(1).to_bytes(1, byteorder='big')
        }
        frame_type = type_dict[frame_type_]
        length = len(payload_).to_bytes(4, byteorder='big')
        return frame_type, length

    def close(self):
        self.alive = False

class HTTPServer:
    def __init__(self, host="127.0.0.1", port=8080):
        self.host = host
        self.port = port
        self.socket = None
        self.static_path = None
        self.client_handler = None

    def run(self):
        self.socket = qs.QUICServer()
        self.socket.listen((self.host, self.port))
        print(f'Server running on http://{self.host}:{self.port}')

        while True:
            if self.client_handler is None:
                self.socket.accept()
                print(f'Client {self.socket.client_addr} connected\n')
                self.client_handler = Client_Handler(self.socket, self.socket.client_addr, self.static_path)
            if self.client_handler and not self.client_handler.alive:
                self.client_handler = None
                self.socket = qs.QUICServer()
                self.socket.listen((self.host, self.port))
            time.sleep(0.01)

        
    
    def set_static(self, path):
        self.static_path = path
    
    def close(self):
        self.socket.close()
        if self.client_handler:
            self.client_handler.close()