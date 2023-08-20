import socket
import struct
import threading
import time

# sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num
# recv_setup, recv_syn, recv_ack, recv_stream_id, recv_last_num, recv_now_num

ack_time_out = 1.0
unit_block_size = 1000

class buffer_unit:
    def __init__(self, stream_id, window_size, flow_window):
        self.stream_id = stream_id
        self.last_num = None
        self.data = []
        self.acks = []
        self.head = -1
        self.last = window_size
        self.now = 0
        self.flow_control_remain = flow_window
        self.timer_dict = dict()
        self.lock_acks = threading.Lock()
        self.lock_window = threading.Lock()
        self.lock_timer = threading.Lock()
        
    def sent_init(self, data):
        data_list = [data[i:i + unit_block_size] for i in range(0, len(data), unit_block_size)]
        self.last_num = len(data_list) - 1
        for i in range(len(data_list)):
            self.data.append(data_list[i])
            self.acks.append(False)
        if self.last > self.last_num:
            self.last = self.last_num
    
    def get_stream_id(self):
        return self.stream_id
    def get_last_num(self):
        return self.last_num
    
    def get_data(self, num):
        return self.data[num]
    def get_acks(self):
        self.lock_acks.acquire()
        acks = self.acks
        self.lock_acks.release()
        return acks
    def get_specific_ack(self, num):
        self.lock_acks.acquire()
        ack = self.acks[num]
        self.lock_acks.release()
        return ack
    def update_acks(self, num):
        self.lock_acks.acquire()
        self.acks[num] = True
        self.lock_acks.release()
    def get_head(self):
        self.lock_window.acquire()
        head = self.head
        self.lock_window.release()
        return head
    def plus_head(self):
        self.lock_window.acquire()
        self.head += 1
        self.lock_window.release()
    def get_last(self):
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
    def get_now(self):
        now = self.now
        return now
    def plus_now(self):
        self.now += 1
    def get_flow_control_remain(self):
        self.lock_window.acquire()
        flow = self.flow_control_remain
        self.lock_window.release()
        return flow
    def update_flow_control_remain(self, num):
        self.flow_control_remain = num
    
    def get_timer_dict(self):
        self.lock_timer.acquire()
        timer_dict = self.timer_dict
        self.lock_timer.release()
        return timer_dict
    def insert_timer_dict(self, num, times):
        self.lock_timer.acquire()
        self.timer_dict[num] = times
        self.lock_timer.release()

class QUICClient:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_addr = None
        
        self.client_congestion_window_size = 5
        self.client_flow_control_window_size = 10000
        
        self.sent_buffer = None # 我不知道要幹嘛用的 笑死
        self.recv_buffer = dict() # key = stream id, val = (now_num, data)
        self.recv_queue = []
        self.lock_recv_queue = threading.Lock()
        
        self.stream_dict = dict()
        self.thread_sent = None # 我不知道要幹嘛用的 笑死+1
        self.thread_sent_list = []
        self.thread_recv = None
        self.thread_recv_stop_flag = False
        
        
    def connect(self, socket_addr):
        """connect to the specific server"""
        self.server_addr = socket_addr
        # 第一次握手
        sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num = 1, 1, 0, 0, 0, 0
        sent_hdr = struct.pack('!BBBBBB', sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num)
        sent_payload = self.client_flow_control_window_size.to_bytes(2, byteorder='big')
        sent_packet = sent_hdr + sent_payload
 
        timeout = self.client_socket.gettimeout()
        self.client_socket.settimeout(ack_time_out)
        while True:
            try:
                self.client_socket.sendto(sent_packet, self.server_addr)
                recv_packet = self.client_socket.recv(1024)
                recv_hdr = recv_packet[:6]
                recv_payload = recv_packet[6:]
                recv_setup, recv_syn, recv_ack, recv_stream_id, recv_last_num, recv_now_num = struct.unpack('!BBBBBB',recv_hdr)
                # print(recv_setup, recv_syn, recv_ack, recv_stream_id, recv_last_num, recv_now_num)
                if recv_setup == 1 and recv_syn == 1 and recv_ack == 1:
                    break
            except socket.timeout:
                print('第一次握手失敗，重新傳送')
        self.client_socket.settimeout(timeout)
        recv_flow_control_window_size = int.from_bytes(recv_payload, byteorder='big')
        self.client_window_size = max(recv_flow_control_window_size, self.client_flow_control_window_size)
        
        # 第三次握手
        sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num = 1, 0, 1, 0, 0, 0
        sent_hdr = struct.pack('!BBBBBB', sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num)
        sent_payload = self.client_flow_control_window_size.to_bytes(2, byteorder='big')
        sent_packet = sent_hdr + sent_payload
        self.client_socket.sendto(sent_packet, self.server_addr)
        
        # 開啟 thread 來 recv packet 如果是 1, 0, 1, 0, 0, 0 就繼續送第三次握手 不是的話就丟進 recv buffer
        self.thread_recv = threading.Thread(target=self.recv_thread)
        self.thread_recv.start()
        
        # 開啟 thread 來 send packet (開個球 根本不需要)
        # self.sent_thread = threading.Thread(self.sent_thread)
        # self.sent_thread.start()
    
    def send(self, stream_id: int, data: bytes):
        """call this method to send data, with non-reputation stream_id"""
        # self.server_socket.send(packet)
        unit = buffer_unit(stream_id=stream_id, window_size=self.client_congestion_window_size, flow_window=self.client_flow_control_window_size)
        unit.sent_init(data)
        self.stream_dict[stream_id] = unit
        sent_thread = threading.Thread(target=self.sent_thread, args=(stream_id, 0))
        sent_thread.start()
        self.thread_sent_list.append(sent_thread)
    
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
                
    
    def close(self):
        """close the connection and the socket"""
        for th in self.thread_sent_list:
            th.join()
        sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num = 1, 0, 0, 0, 0, 0
        sent_hdr = struct.pack('!BBBBBB', sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num)
        self.client_socket.sendto(sent_hdr, self.server_addr)
        self.client_socket.close()
        
    def sent_thread(self, stream_id: int, pad):
        unit = self.stream_dict[stream_id]
        time_thread = threading.Thread(target=self.sent_check_timer, args=(unit, 0))
        time_thread.start()
        
        while True:
            while unit.get_now() <= unit.get_last() and unit.get_flow_control_remain() > 0 and unit.get_now() <= unit.get_last():
                sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num = 0, 0, 0, unit.get_stream_id(), unit.get_last_num(), unit.get_now()
                sent_hdr = struct.pack('!BBBBBB', sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num)
                sent_payload = unit.get_data(unit.get_now())
                sent_packet = sent_hdr + sent_payload
                self.client_socket.sendto(sent_packet, self.server_addr)
                unit.insert_timer_dict(unit.get_now(), time.time())
                unit.plus_now()
                
            # 全部都ack了 就掰掰
            flag = True
            for ackk in unit.get_acks():
                if ackk == False:
                    flag = False
                    break
            if flag:
                break
        
        time_thread.join()
    
    def sent_check_timer(self, unit: int, pad):
        while True:
            for key, val in unit.get_timer_dict().items():
                if time.time() - val > 1 and unit.get_specific_ack(key):
                    sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num = 0, 0, 0, unit.get_stream_id(), unit.get_last_num(), key
                    sent_hdr = struct.pack('!BBBBBB', sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num)
                    sent_payload = unit.get_data(key)
                    sent_packet = sent_hdr + sent_payload
                    print(sent_hdr)
                    self.client_socket.sendto(sent_packet, self.server_addr)
                    unit.insert_timer_dict(key, time.time())
            
            flag = True
            for ackk in unit.get_acks():
                if ackk == False:
                    flag = False
                    break
            if flag:
                break
            time.sleep(0.1)
    
    def recv_thread(self):
        # 如果是 1, 1, 1, 0, 0, 0 就繼續送第三次握手 不是的話就丟進 recv buffer
        while True:
            recv_packet = self.client_socket.recv(1024)
            recv_hdr = recv_packet[:6]
            recv_payload = recv_packet[6:]
            recv_setup, recv_syn, recv_ack, recv_stream_id, recv_last_num, recv_now_num = struct.unpack('!BBBBBB',recv_hdr)
            # print(recv_setup, recv_syn, recv_ack, recv_stream_id, recv_last_num, recv_now_num)
            if recv_setup == 1 and recv_syn == 1 and recv_ack == 1:
                sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num = 1, 0, 1, 0, 0, 0
                sent_hdr = struct.pack('!BBBBBB', sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num)
                sent_payload = self.client_window_size.to_bytes(1, byteorder='big')
                sent_packet = sent_hdr + sent_payload
                self.client_socket.sendto(sent_packet, self.server_addr)
            else:
                # 收到正常的 packet
                if recv_setup == 0 and recv_syn == 0 and recv_ack == 0:
                    if recv_stream_id not in self.recv_buffer:
                        self.recv_buffer[recv_stream_id] = []
                    if (recv_now_num, recv_payload) not in self.recv_buffer[recv_stream_id]:
                        self.recv_buffer[recv_stream_id].append((recv_now_num, recv_payload))
                    ack_reply_thread = threading.Thread(target=self.ack_reply, args=(recv_stream_id, recv_last_num, recv_now_num, recv_payload))
                    ack_reply_thread.start()
                # 收到你媽的 ack
                elif recv_setup == 0 and recv_syn == 0 and recv_ack == 1:
                    ack_process_thread = threading.Thread(target=self.ack_process, args=(recv_stream_id, recv_now_num, recv_last_num, recv_payload))
                    ack_process_thread.start()
                # break
                elif recv_setup == 1 and recv_syn == 0 and recv_ack == 0:
                    break

    def process_recv_buffer(self, recv_stream_id, pad):
        self.recv_buffer[recv_stream_id].sort(key=lambda x: x[0])
        tmp_data = b''
        for itt, data in self.recv_buffer[recv_stream_id]:
            tmp_data += data
        self.lock_recv_queue.acquire()
        self.recv_queue.append((recv_stream_id ,tmp_data))
        self.lock_recv_queue.release()
    
    def ack_reply(self, recv_stream_id, recv_last_num, recv_now_num, recv_payload):
        # 回傳ack
        sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num = 0, 0, 1, recv_stream_id, recv_last_num, recv_now_num
        sent_hdr = struct.pack('!BBBBBB', sent_setup, sent_syn, sent_ack, sent_stream_id, sent_last_num, sent_now_num)
        sent_payload = self.client_flow_control_window_size.to_bytes(2, byteorder='big')
        sent_packet = sent_hdr + sent_payload
        self.client_socket.sendto(sent_packet, self.server_addr)
        
        # 如果 recv buffer 沒有這筆資料 就加進去 再確認要不要丟出來到 queue 裡面
        if len(self.recv_buffer[recv_stream_id]) == recv_last_num + 1:
            process_recv_buffer_thread = threading.Thread(target=self.process_recv_buffer, args=(recv_stream_id, 0))
            process_recv_buffer_thread.start()
        
    def ack_process(self, recv_stream_id, recv_now_num, recv_last_num, recv_payload):
        self.stream_dict[recv_stream_id].update_acks(recv_now_num)
        recv_window_size = int.from_bytes(recv_payload, byteorder='big')
        if self.stream_dict[recv_stream_id].get_head() + 1 == recv_now_num:
            self.stream_dict[recv_stream_id].plus_head()
            self.stream_dict[recv_stream_id].plus_last()
        self.stream_dict[recv_stream_id].update_flow_control_remain = recv_window_size
        
            
# client side
if __name__ == "__main__":
    client = QUICClient()
    client.connect(("127.0.0.1", 30000))
    recv_id, recv_data = client.recv()
    print(recv_data.decode("utf-8")) # SOME DATA, MAY EXCEED 1500 bytes
    client.send(2, b"Hello Server!")
    client.close()