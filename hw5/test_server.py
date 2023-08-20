import socket

# Create a UDP socket and bind it to IP address 0.0.0.0 and port 8888
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', 8888))

# Wait for incoming messages and print them to the console
while True:
    data, address = server_socket.recvfrom(1024)
    print(f"Received message from {address}: {data.decode()}")
