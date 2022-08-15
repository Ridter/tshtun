from libs.pel import PEL_Server
from libs.ptyshell import Shell
from socket import *

listen_sock = socket()
listen_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listen_sock.bind(("0.0.0.0", 6666))
listen_sock.listen(1)

conn, addr = listen_sock.accept()
print("Connect from", addr)
pel = PEL_Server(conn=conn)
init = pel.pel_client_init()
pty = Shell(conn, pel)
pty.handle()