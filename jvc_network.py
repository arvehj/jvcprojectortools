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

class Closed(Exception):
    """Connection Closed"""
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
        self.host_port = None

    def connect(self):
        """Open network connection to projector and perform handshake"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self.print_send:
                print('    - connecting...')
            self.socket.connect(self.host_port)
            if self.print_send:
                print('    - connected')
        except Exception as err:
            raise Error('Connection failed', err)
        self.expect(b'PJ_OK')
        self.send(b'PJREQ')
        self.expect(b'PJACK')

    def __enter__(self):
        try:
            with open(conf_file, 'r') as f:
                conf = json.load(f)
        except:
            conf = dict()
        save_conf = False

        while True:
            if not conf.get('host', None):
                print('\nIf you have configured a hostname for your projector (usually in your\n'
                      'internet gateway) enter that hostname here.\n'
                      'If you don'"'"'t have a hostname, you can use the "IP Address" displayed \n'
                      'in the "Network" menu (found under the "Function" main menu) on the\n'
                      'projector. If "DHCP Client" is "Off" change it to "On" then select "Set"\n'
                      'to have the "IP Address" information filled out.\n')
                conf['host'] = input('Enter hostname or ip address: ')
                save_conf = True

            if not conf.get('port', None):
                conf['port'] = 20554
                save_conf = True

            try:
                self.host_port = (conf['host'], conf['port'])
                self.connect()
            except Exception as err:
                print('Failed to connect to {}:{}'.format(conf['host'], conf['port']))
                if isinstance(err, Error):
                    print(err.args[1])
                else:
                    print(err)

                print('\nCheck that nothing else is connected, as the projector only supports a\n'
                      'single connection at a time. Then enter "r" to retry with the same network\n'
                      'network address, enter "n" to try a new network address, or enter "a" to')
                ret = input('abort. [r/n/a]: ')
                if ret == 'n':
                    conf['host'] = None
                    conf['port'] = None
                    continue
                if ret == 'r':
                    continue
                raise err
            break

        if save_conf:
            with open(conf_file, 'w') as f:
                json.dump(conf, f)

        return self

    def close(self):
        """Close socket"""
        if self.print_send:
            print('    - close socket')
        self.socket.close()

    def __exit__(self, exception, value, traceback):
        self.close()

    def reconnect(self):
        """Re-open network connection"""
        self.close()
        self.connect()

    def send(self, data):
        """Send data with optional data dump"""
        if self.print_send:
            dumpdata.dumpdata('    > Send:    ', '{:02x}', data)
        try:
            self.socket.send(data)
        except ConnectionAbortedError as err:
            raise Closed(err)

    def recv(self, limit=1024, timeout=0):
        """Receive data with optional timeout and data dump"""
        if timeout:
            ready = select.select([self.socket], [], [], timeout)
            if not ready[0]:
                raise Timeout('{} second timeout expired'.format(timeout))
        data = self.socket.recv(limit)
        if not len(data):
            raise Closed('Connection closed by projector')
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
