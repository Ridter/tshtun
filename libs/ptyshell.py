#!/usr/bin/env python3
import select
import os
import socket
import shutil
import pty, tty
from struct import pack


class Shell:
    def __init__(self, socks, pel):
        self.socks = socks
        self.pel = pel

    def handle(self):
        csock = self.socks
        try:
            fsock = csock.fileno()
        except socket.timeout:
            print(e)
            return 0
        self.pel.pel_send_msg(os.getenv("TERM", "xterm"))
        cols, rows = shutil.get_terminal_size()
        _tmp = pack("!HH", rows, cols)
        self.pel.pel_send_msg(_tmp)
        self.pel.pel_send_msg("bash")
        old_tc = tty.tcgetattr(pty.STDIN_FILENO)
        tty.setraw( pty.STDIN_FILENO )
        print ("[x] Ok....\r")
        try:
            while True:
                r, w, e = select.select( [ fsock, pty.STDIN_FILENO ], [], [] )
                if fsock in r:
                    dat = self.pel.pel_recv_msg()
                    if dat:
                        os.write( pty.STDOUT_FILENO, dat )
                    else:
                        tty.tcsetattr(pty.STDIN_FILENO, tty.TCSADRAIN, old_tc)
                        break

                if pty.STDIN_FILENO in r:
                    dat = os.read( pty.STDIN_FILENO, 1000 )
                    self.pel.pel_send_msg(dat)
        finally:
            tty.tcsetattr(pty.STDIN_FILENO, tty.TCSADRAIN, old_tc)
            print ("[!] client close connection....\r")
            csock.close()
            return 0