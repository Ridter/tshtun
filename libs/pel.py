import hashlib
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

SECRET = "ThisisADemo"
BUFSIZE = 4096
CHALLENGE =  b"\x58\x90\xAE\x86\xF1\xB9\x1C\xF6\x29\x83\x95\x71\x1D\xDE\x58\x0D"

class PEL_Server:
    def __init__(self, conn) -> None:
        self.conn = conn
        self.send_ipad      = b""
        self.send_opad      = b""
        self.send_p_cntr    = 0
        self.recv_ipad      = b""
        self.recv_opad      = b""
        self.recv_p_cntr    = 0
        self.send_aes_key   = b""
        self.recv_aes_key   = b""
        self.send_IV        = b""
        self.recv_IV        = b""

    def pel_setup_context(self, IV):
        key = hashlib.sha1(SECRET.encode())
        key.update(IV)
        key = key.digest()
        aes_key = key[:16]
        k_ipad = b"\x36" * 64
        k_opad = b"\x5C" * 64

        _t_ipad = bytearray(k_ipad)
        _t_opad = bytearray(k_opad)
        for i in range(20):
            _t_ipad[i] = _t_ipad[i] ^ key[i]
            _t_opad[i] = _t_opad[i] ^ key[i]
        ipad = bytes(_t_ipad)
        opad = bytes(_t_opad)
        p_cntr = 0
        return aes_key, ipad, opad, p_cntr

    def pel_recv_all(self, count):
        buffer = b""
        while len(buffer) < count:
            tmp = self.conn.recv(min(65536, count - len(buffer)))
            if not tmp:
                break
            buffer = buffer + tmp
        return buffer

    def pel_send_all(self, data):
        self.conn.sendall(data, 0)

    def pel_recv_msg(self):
        try:
            #  /* receive the first encrypted block */
            data = self.pel_recv_all(16)
            ciphertext = data
            cypher = AES.new(self.recv_aes_key, AES.MODE_CBC, self.recv_IV)
            data_len_msg = cypher.decrypt(data)
            data_len = (data_len_msg[0] << 8) + data_len_msg[1]
            # /* verify the message length */
            if data_len < 0 or data_len > BUFSIZE:
                print("[-] PEL_BAD_MSG_LENGTH")
                return None
            blk_len = 2 + data_len
            if  (blk_len & 0x0F) != 0:
                blk_len += 16 - (blk_len & 0x0F)
            #/* receive the remaining ciphertext and the mac */
            all_data =  self.pel_recv_all(blk_len - 16 + 20 )
            ciphertext += all_data
            hmac = ciphertext[blk_len:blk_len+20]
            # /* verify the ciphertext integrity */
            _ciphertext = bytearray(ciphertext)
            _ciphertext[blk_len    ]   = (self.recv_p_cntr << 24) & 0xFF
            _ciphertext[blk_len + 1]   = (self.recv_p_cntr << 16) & 0xFF
            _ciphertext[blk_len + 2]   = (self.recv_p_cntr << 8) & 0xFF
            _ciphertext[blk_len + 3]   = (self.recv_p_cntr) & 0xFF
            ciphertext = bytes(_ciphertext)
            _digest = hashlib.sha1(self.recv_ipad)
            _digest.update(ciphertext[:blk_len + 4])
            _digest = _digest.digest()

            digest = hashlib.sha1(self.recv_opad)
            digest.update(_digest)
            digest = digest.digest()
        
            if hmac != digest:
                print("[-] PEL_CORRUPTED_DATA")
                return None

            # /* increment the packet counter */
            self.recv_p_cntr += 1

            # /* decrypt the ciphertext */
            cypher = AES.new(self.recv_aes_key, AES.MODE_CBC, self.recv_IV)
            
            plain_data = cypher.decrypt(ciphertext[:blk_len])
            self.recv_IV = ciphertext[blk_len-16:blk_len]
            msg = plain_data[2:2+data_len]
            return msg
        except Exception as e:
            print("[-] PEL_RECV_MSG_ERROR: ", e)
            return None
        
    def pel_send_msg(self, msg):
        try:
            # /* verify the message length */
            if type(msg) == str:
                msg = msg.encode()
            length = len(msg)
            if length <= 0 or length > BUFSIZE:
                print("[-] PEL_BAD_MSG_LENGTH")
                return False
            #/* write the message length at start of buffer */
            _data_len_msg = bytearray(2)
            _data_len_msg[0] = (length >> 8) & 0xFF
            _data_len_msg[1] = (length) & 0xFF
            buffer = _data_len_msg + bytearray(msg)
            msg = bytes(buffer)
            # /* round up to AES block length (16 bytes) */
            blk_len = 2 + length;

            if (blk_len & 0x0F ) != 0 :
                blk_len += 16 - ( blk_len & 0x0F)
            #/* encrypt the buffer with AES-CBC-128 */
            cypher = AES.new(self.send_aes_key, AES.MODE_CBC, self.send_IV)
            
            encrypted_data = cypher.encrypt(pad(msg, 16))

            self.send_IV = encrypted_data[blk_len-16:blk_len]
            _buffer = bytearray(4)
            _buffer[0]   = (self.send_p_cntr << 24) & 0xFF
            _buffer[1]   = (self.send_p_cntr << 16) & 0xFF
            _buffer[2]   = (self.send_p_cntr << 8) & 0xFF
            _buffer[3]   = (self.send_p_cntr) & 0xFF

            buffer = bytes(bytearray(encrypted_data) + _buffer)

            # /* compute the HMAC-SHA1 of the ciphertext */
            _digest = hashlib.sha1(self.send_ipad)
            _digest.update(buffer)
            _digest = _digest.digest()

            digest = hashlib.sha1(self.send_opad)
            digest.update(_digest)
            digest = digest.digest()

            # /* increment the packet counter */
            self.send_p_cntr += 1

            # /* send the ciphertext and the HMAC */
            finnal = bytes(bytearray(encrypted_data) + bytearray(digest))
            self.pel_send_all(finnal[:blk_len+20])
            return True
        except Exception as e:
            print(e)
            return False

    def pel_server_init(self):
        try:
            # /* get the IVs from the client */
            data = self.conn.recv(40)
            IV2 = data[:20]
            IV1 = data[20:]
            self.send_aes_key, self.send_ipad, self.send_opad, self.send_p_cntr = self.pel_setup_context(IV1)
            self.recv_aes_key, self.recv_ipad, self.recv_opad, self.recv_p_cntr = self.pel_setup_context(IV2)
            self.recv_IV = IV2[:16]
            self.send_IV = IV1[:16]
            #  /* handshake - decrypt and verify the client's challenge */
            handshake = self.pel_recv_msg()
            if handshake is None:
                print("[-] PEL_WRONG_CHALLENGE")
                return None

            #  /* send the server's challenge */
            msg = CHALLENGE
            self.pel_send_msg(msg)
        except Exception as e:
            print(e)
            return None


    def pel_client_init(self):
        #/* generate both initialization vectors */
        try:
            random_1 = os.urandom(16)
            random_2 = os.urandom(16)
            _tmp1 = hashlib.sha1(random_1)
            _tmp2 = hashlib.sha1(random_2)
            IV1 = _tmp1.digest()
            IV2 = _tmp2.digest()
            data = IV1 + IV2
            self.pel_send_all(data)
            self.send_aes_key, self.send_ipad, self.send_opad, self.send_p_cntr = self.pel_setup_context(IV1)
            self.recv_aes_key, self.recv_ipad, self.recv_opad, self.recv_p_cntr = self.pel_setup_context(IV2)
            self.recv_IV = IV2[:16]
            self.send_IV = IV1[:16]
            msg = CHALLENGE
            self.pel_send_msg(msg)
            handshake = self.pel_recv_msg()
            if handshake == msg:
                return True
        except Exception as e:
            print(e)
            return False