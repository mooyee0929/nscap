import struct

length: int = 3
type: int = 2
flags: int = 5
stream_id: int = 1
payload: bytes = b""
length = len(payload)
pack_str = f"!3sBBI{length}s"
test = struct.pack(pack_str, length.to_bytes(3, 'big'), type, flags, stream_id, payload)
print(test)
open = struct.unpack("!3sBBI", test)
print(open)