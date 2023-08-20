import threading
import time
import socket
from QUIC import quic_client as qc

class Response:
    def __init__(self, stream_id, recv_dict, header_dict):
        self.stream_id = stream_id
        self.recv_dict = recv_dict
        self.header_dict = header_dict

    def get_headers(self):
        return self.header_dict
    
    def get_full_body(self):
        while not self.recv_dict[self.stream_id]['complete']:
            time.sleep(0.01)
        return self.recv_dict[self.stream_id]['data']

    def get_stream_content(self):
        while not self.recv_dict[self.stream_id]['complete']:  
            time.sleep(0.01)
        if self.recv_dict[self.stream_id]['data'] is None:
            return None
        else:
            content = self.recv_dict[self.stream_id]['data']
            self.recv_dict[self.stream_id]['data'] = None
            return content
        

class HTTPClient: # For HTTP/3
    def __init__(self):
        self.socket = None
        self.connection = False
        # self.recv_buffer = None
        self.recv_dict = dict()
        self.next_stream_id = 1
        self.recv_thread = None
        self.header_dict = None

    def get(self, url, headers=None):
        # url = "http://127.0.0.1:8080/static/xxx.txt"
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

        self.connect(host, port)

        payload = f'method: GET\r\npath: {path}'.encode('utf-8')
        frame_type, length = self.make_header('hdr_frame', payload)
        frame = frame_type + length + payload
        stream_id = self.next_stream_id
        self.next_stream_id+=2

        self.recv_dict[stream_id] = {'complete':False, 'data':b'', 'first':False, 'length':0}

        self.send(stream_id, frame, True)

        
        while not self.header_dict:
            time.sleep(0.001)

        response = Response(stream_id, self.recv_dict, self.header_dict)
        return response

    def recv(self):
        while self.connection:
            try:
                # self.socket.sock.settimeout(5)
                stream_id, frame, flag = self.socket.recv()
                if stream_id is None:
                    print('stream_id is None')
                    self.connection = False
                    self.socket.close()
                    break
                # print(f'RECV # stream_id: {stream_id} flag: {flag}')
                if self.recv_dict[stream_id]['first']:
                    self.recv_dict[stream_id]['data'] += frame
                    if self.recv_dict[stream_id]['length'] == len(self.recv_dict[stream_id]['data']):
                        self.recv_dict[stream_id]['complete'] = True
                    continue
                frame_type = frame[0]
                length = int.from_bytes(frame[1:5], byteorder='big')
                payload = frame[5:].decode('utf-8')
                self.recv_dict[stream_id]['length'] = length
                #data frame
                if frame_type == 0:
                    self.recv_dict[stream_id]['data'] += payload.encode('utf-8')
                    self.recv_dict[stream_id]['first'] = True
                    if flag:
                            self.recv_dict[stream_id]['complete'] = True
                #hdr frame
                elif frame_type == 1:
                    item_list = payload.split('\r\n')
                    payload_dict = {key: val for item in item_list for key, val in [item.split(': ')]}
                    self.header_dict = payload_dict
            except:
                self.connection = False
                self.socket.close()
                break

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

    def connect(self, host, port):
        if not self.connection:
            self.socket = qc.QUICClient()
            self.socket.drop(5)
            self.recv_buffer = b''
            self.recv_streams = dict()

            try:
                self.socket.connect((host, port))
                self.connection = True
                self.recv_thread = threading.Thread(target=self.recv)
                self.recv_thread.start()
            except:
                self.connection = False
                self.socket.close()

