#!/usr/bin/env python3

"""JVC projector network connection module"""

import json
import select
import socket
import dumpdata

conf_file = 'jvc_network.conf'

class Error(Exception):
    """Error"""
    pass

class Timeout(Exception):
    """Command Timout"""
    pass

class JVCNetwork:
    """JVC projector network connection"""
    def __init__(self, print_all=False, print_recv=False, print_send=False):
        self.print_recv = print_recv or print_all
        self.print_send = print_send or print_all
        self.socket = None

    def __enter__(self):
        try:
            with open(conf_file, 'r') as f:
                conf = json.load(f)
        except:
            conf = dict()
        save_conf = False

        if not conf.get('host', None):
            conf['host'] = input('Enter hostname or ip: ')
            save_conf = True

        if not conf.get('port', None):
            conf['port'] = int(input('Enter port number (e.g. 20554): '))
            save_conf = True

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self.print_send:
                print('    - connecting...')
            self.socket.connect((conf['host'], conf['port']))
            if self.print_send:
                print('    - connected')
        except (ConnectionRefusedError, TimeoutError) as err:
            raise Error('Connection failed', err)
        self.expect(b'PJ_OK')
        self.send(b'PJREQ')
        self.expect(b'PJACK')

        if save_conf:
            with open(conf_file, 'w') as f:
                json.dump(conf, f)

        return self

    def __exit__(self, exception, value, traceback):
        if self.print_send:
            print('    - close socket')
        self.socket.close()

    def send(self, data):
        """Send data with optional data dump"""
        if self.print_send:
            dumpdata.dumpdata('    > Send:    ', '{:02x}', data)
        self.socket.send(data)

    def recv(self, limit=1024, timeout=0):
        """Receive data with optional timeout and data dump"""
        if timeout:
            ready = select.select([self.socket], [], [], timeout)
            if not ready[0]:
                raise Timeout()
        data = self.socket.recv(limit)
        if self.print_recv:
            dumpdata.dumpdata('    < Received:', '{:02x}', data)
        return data

    def expect(self, res, timeout=1):
        """Receive data and compare it against expected data"""
        data = self.recv(len(res), timeout)
        if data != res:
            raise Error('Expected', res)

if __name__ == "__main__":
    print('test jvc ip connect')
    try:
        with JVCNetwork(print_recv=True, print_send=True) as jvc:
            pass
    except Error as err:
        print('Error', err)
