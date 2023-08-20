import struct
import ctypes

class MyHeader(ctypes.BigEndianStructure):
    _fields_ = [
        ("int_1", ctypes.c_uint8),
        ("int_2", ctypes.c_uint8),
        ("int_3", ctypes.c_uint8),
    ]

h = MyHeader(1,2,3)
bytes_str = bytes(h)
print(bytes_str)
h = MyHeader.from_buffer_copy(bytes_str)
print(h.int_1,h.int_2,h.int_3)





