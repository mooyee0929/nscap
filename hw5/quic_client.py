import socket
import struct
import threading
import time


ack_time_out = 1.0
unit_block_size = 1024

class Packet:
    def __init__(self, stream_id, window_size, flow_window):
        self.lock_acks = threading.Lock()
        self.lock_window = threading.Lock()
        self.lock_timer = threading.Lock()
        self.stream_id = stream_id
        self.last_num = None
        self.data = []
        self.acks = []
        self.head = -1
        
        self.now = 0
        self.last = window_size

        self.flow_control_remain = flow_window
        self.time = dict()
        
    def sent_init(self, data):
        data_list = [data[i:i + unit_block_size] for i in range(0, len(data), unit_block_size)]
        self.last_num = len(data_list) - 1
        for i in range(len(data_list)):
            self.data.append(data_list[i])
            self.acks.append(False)
        if self.last > self.last_num:
            self.last = self.last_num

    
    def return_data(self, num):
        return self.data[num]
    def return_acks(self):
        self.lock_acks.acquire()
        acks = self.acks
        self.lock_acks.release()
        return acks
    def return_specific_ack(self, num):
        self.lock_acks.acquire()
        ack = self.acks[num]
        self.lock_acks.release()
        return ack
    def update_acks(self, num):
        self.lock_acks.acquire()
        self.acks[num] = True
        self.lock_acks.release()
    def return_head(self):
        self.lock_window.acquire()
        head = self.head
        self.lock_window.release()
        return head
    def plus_head(self):
        self.lock_window.acquire()
        self.head += 1
        self.lock_window.release()
    def return_last(self):
        self.lock_window.acquire()
        last = self.last
        self.lock_window.release()
        return last
    def plus_last(self):
        self.lock_window.acquire()
        self.last += 1
        if self.last > self.last_num:
            self.last = self.last_num
        self.lock_window.release()

    def return_flow_control_remain(self):
        self.lock_window.acquire()
        flow = self.flow_control_remain
        self.lock_window.release()
        return flow
    def return_timer_dict(self):
        self.lock_timer.acquire()
        time = self.time
        self.lock_timer.release()
        return time
    def insert_timer_dict(self, num, times):
        self.lock_timer.acquire()
        self.time[num] = times
        self.lock_timer.release()

class QUICClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server = None
        
        self.congestion_control = 8
        self.flow_control = 10240
        
        self.recv_buffer = dict() # key = stream id, val = (now_num, data)
        self.recv_queue = []
        self.lock_recv_queue = threading.Lock()
        
        self.stream = dict()
        self.thread_sent_list = []
        self.thread_recv = None
        self.thread_recv_stop_flag = False
        
        
    def process_buffer(self, r_stream_id, pad):
        self.recv_buffer[r_stream_id].sort(key=lambda x: x[0])
        tmp_data = b''
        for itt, data in self.recv_buffer[r_stream_id]:
            tmp_data += data
        self.lock_recv_queue.acquire()
        self.recv_queue.append((r_stream_id ,tmp_data))
        self.lock_recv_queue.release()
    
    def re_ack(self, r_stream_id, r_last_num, r_now_num, r_payload):
        # 回傳ack
        s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num = 0, 0, 1, r_stream_id, r_last_num, r_now_num
        s_hdr = struct.pack('!BBBBBB', s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num)
        s_payload = self.flow_control.to_bytes(2, byteorder='big')
        s_packet = s_hdr + s_payload
        self.sock.sendto(s_packet, self.server)
        
        # 如果 recv buffer 沒有這筆資料 就加進去
        if len(self.recv_buffer[r_stream_id]) == r_last_num + 1:
            process_buffer_thread = threading.Thread(target=self.process_buffer, args=(r_stream_id, 0))
            process_buffer_thread.start()
        
    def process_ack(self, r_stream_id, r_now_num, r_last_num, r_payload):
        self.stream[r_stream_id].update_acks(r_now_num)
        recv_window_size = int.from_bytes(r_payload, byteorder='big')
        if self.stream[r_stream_id].return_head() + 1 == r_now_num:
            self.stream[r_stream_id].plus_head()
            self.stream[r_stream_id].plus_last()
        self.stream[r_stream_id].flow_control_remain = recv_window_size

    def connect(self, socket_addr):
        """connect to the specific server"""
        self.server = socket_addr
        # 第一次握手
        s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num = 1, 1, 0, 0, 0, 0
        s_hdr = struct.pack('!BBBBBB', s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num)
        s_payload = self.flow_control.to_bytes(2, byteorder='big')
        s_packet = s_hdr + s_payload
 
        timeout = self.sock.gettimeout()
        self.sock.settimeout(ack_time_out)
        while True:
            try:
                self.sock.sendto(s_packet, self.server)
                r_packet = self.sock.recv(1024)
                r_hdr = r_packet[:6]
                r_payload = r_packet[6:]
                r_setup, r_syn, r_ack, r_stream_id, r_last_num, r_now_num = struct.unpack('!BBBBBB',r_hdr)

                if r_setup == 1 and r_syn == 1 and r_ack == 1:
                    break
            except socket.timeout:
                print('握手失敗，重新傳送')
        self.sock.settimeout(timeout)
        recv_flow_control_window_size = int.from_bytes(r_payload, byteorder='big')
        self.client_window_size = max(recv_flow_control_window_size, self.flow_control)
        
        # 第三次握手
        s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num = 1, 0, 1, 0, 0, 0
        s_hdr = struct.pack('!BBBBBB', s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num)
        s_payload = self.flow_control.to_bytes(2, byteorder='big')
        s_packet = s_hdr + s_payload
        self.sock.sendto(s_packet, self.server)
        
        # thread recv packet 
        self.thread_recv = threading.Thread(target=self.recv_thread)
        self.thread_recv.start()
        

    def send(self, stream_id: int, data: bytes):
        """call this method to send data, with non-reputation stream_id"""
        pack = Packet(stream_id=stream_id, window_size=self.congestion_control, flow_window=self.flow_control)
        pack.sent_init(data)
        self.stream[stream_id] = pack
        sent_thread = threading.Thread(target=self.sent_thread, args=(stream_id, 0))
        sent_thread.start()
        self.thread_sent_list.append(sent_thread)


    def sent_thread(self, stream_id: int, pad):
        pack = self.stream[stream_id]
        time_thread = threading.Thread(target=self.sent_check_timer, args=(pack, 0))
        time_thread.start()
        
        while True:
            while pack.now <= pack.return_last() and pack.return_flow_control_remain() > 0:
                s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num = 0, 0, 0, pack.stream_id, pack.last_num, pack.now
                s_hdr = struct.pack('!BBBBBB', s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num)
                s_payload = pack.return_data(pack.now)
                s_packet = s_hdr + s_payload
                self.sock.sendto(s_packet, self.server)
                pack.insert_timer_dict(pack.now, time.time())
                pack.now += 1
                
            # 全部都ack
            flag = True
            for ackk in pack.return_acks():
                if ackk == False:
                    flag = False
                    break
            if flag:
                break
        
        time_thread.join()
    
    def sent_check_timer(self, pack: int, pad):
        while True:
            for key, val in pack.return_timer_dict().items():
                if time.time() - val > 1 and pack.return_specific_ack(key):
                    s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num = 0, 0, 0, pack.stream_id, pack.last_num, key
                    s_hdr = struct.pack('!BBBBBB', s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num)
                    s_payload = pack.return_data(key)
                    s_packet = s_hdr + s_payload
                    print(s_hdr)
                    self.sock.sendto(s_packet, self.server)
                    pack.insert_timer_dict(key, time.time())
            
            flag = True
            for ackk in pack.return_acks():
                if ackk == False:
                    flag = False
                    break
            if flag:
                break
            time.sleep(0.1)
    
    def recv(self): # stream_id, data
        """receive a stream, with stream_id"""
        stream_id, data = None, None
        while True:
            self.lock_recv_queue.acquire()
            if len(self.recv_queue) != 0:
               stream_id, data = self.recv_queue.pop(0)
               self.lock_recv_queue.release()
               break
            self.lock_recv_queue.release()
            time.sleep(0.1)
            
        return stream_id, data
    
    def recv_thread(self):
        # 如果是 1, 1, 1, 0, 0, 0 就繼續送第三次握手 不是的話就丟進 recv buffer
        while True:
            r_packet = self.sock.recv(1024)
            r_hdr = r_packet[:6]
            r_payload = r_packet[6:]
            r_setup, r_syn, r_ack, r_stream_id, r_last_num, r_now_num = struct.unpack('!BBBBBB',r_hdr)
            if r_setup == 1 and r_syn == 1 and r_ack == 1:
                s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num = 1, 0, 1, 0, 0, 0
                s_hdr = struct.pack('!BBBBBB', s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num)
                s_payload = self.client_window_size.to_bytes(1, byteorder='big')
                s_packet = s_hdr + s_payload
                self.sock.sendto(s_packet, self.server)
            else:
                # 收到packet
                if r_setup == 0 and r_syn == 0 and r_ack == 0:
                    if r_stream_id not in self.recv_buffer:
                        self.recv_buffer[r_stream_id] = []
                    if (r_now_num, r_payload) not in self.recv_buffer[r_stream_id]:
                        self.recv_buffer[r_stream_id].append((r_now_num, r_payload))
                    re_ack_thread = threading.Thread(target=self.re_ack, args=(r_stream_id, r_last_num, r_now_num, r_payload))
                    re_ack_thread.start()
                # 收到ack
                elif r_setup == 0 and r_syn == 0 and r_ack == 1:
                    ack_process_thread = threading.Thread(target=self.process_ack, args=(r_stream_id, r_now_num, r_last_num, r_payload))
                    ack_process_thread.start()
                # break
                elif r_setup == 1 and r_syn == 0 and r_ack == 0:
                    break
                
    
    def close(self):
        """close the connection and the socket"""
        for th in self.thread_sent_list:
            th.join()
        s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num = 1, 0, 0, 0, 0, 0
        s_hdr = struct.pack('!BBBBBB', s_setup, s_syn, s_ack, s_stream_id, s_last_num, s_now_num)
        self.sock.sendto(s_hdr, self.server)
        self.sock.close()
        

    
        
            
# client side
if __name__ == "__main__":
    client = QUICClient()
    client.connect(("127.0.0.1", 30000))
    recv_id, recv_data = client.recv()
    print(recv_data.decode("utf-8")) # SOME DATA, MAY EXCEED 1500 bytes
    client.send(2, b"Hello Server!")
    client.close()