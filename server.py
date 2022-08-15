from libs.pel import PEL_Server
from socket import *

listen_sock = socket()
listen_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listen_sock.bind(("0.0.0.0", 6666))
listen_sock.listen(1)


conn, addr = listen_sock.accept()
print("Connect from", addr)
pel = PEL_Server(conn=conn)
pel.pel_client_init()
# pel.pel_server_init()
# data = pel.pel_recv_msg()
# print(data)
count = 1
import uuid
while True:
    send_data = str(uuid.uuid4())
    msg = "="  * count
    status = pel.pel_send_msg(msg)
    if status is False:
        break
    print("Send datalen: {}".format(len(msg)))
    data = pel.pel_recv_msg()
    if not data:
        break
    print("Recv datalen: {}".format(len(data)))
    count+=1
conn.close()

