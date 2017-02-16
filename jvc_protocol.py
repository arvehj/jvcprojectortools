#!/usr/bin/env python3

"""JVC projector low level command module"""

import enum

import dumpdata
import jvc_network

class Error(Exception):
    """JVC protocol error"""
    pass

class CommandNack(Exception):
    """JVC command not acknowledged"""
    pass

class Header(enum.Enum):
    """JVC command and response headers"""
    operation = b'!'
    reference = b'?'
    response = b'@'
    ack = b'\x06'

UNIT_ID = b'\x89\x01'
END = b'\x0a'

class JVCConnection:
    """JVC projector low level command processing class"""
    def __init__(self, print_cmd_send=False, print_cmd_res=False, print_all=False, **args):
        self.print_cmd_send = print_cmd_send or print_all
        self.print_cmd_res = print_cmd_res or print_all
        self.print_cmd_bin_res = print_all
        self.conn = jvc_network.JVCNetwork(print_all=print_all, **args)

    def __enter__(self):
        self.conn.__enter__()
        return self

    def __exit__(self, exception, value, traceback):
        self.conn.__exit__(exception, value, traceback)

    def _cmd(self, cmdtype, cmd, sendrawdata=None, acktimeout=1):
        """Send command and optional raw data and wait for acks"""
        if self.print_cmd_send:
            print('  > Cmd:', cmdtype, cmdtype.value+cmd)
        assert cmdtype == Header.operation or cmdtype == Header.reference

        self.conn.send(cmdtype.value + UNIT_ID + cmd + END)
        try:
            self.conn.expect(Header.ack.value + UNIT_ID + cmd[:2] + END, timeout=acktimeout)
        except jvc_network.Timeout:
            raise CommandNack(cmdtype, cmd)

        if sendrawdata is None:
            return

        self.conn.send(sendrawdata)
        self.conn.expect(Header.ack.value + UNIT_ID + cmd + END, timeout=20)

    def cmd_op(self, cmd, **kwargs):
        """Send operation command"""
        self._cmd(Header.operation, cmd, **kwargs)

    def cmd_ref(self, cmd, **kwargs):
        """Send reference command and retrieve response"""
        self._cmd(Header.reference, cmd, **kwargs)
        data = self.conn.recv()
        header = Header.response.value + UNIT_ID + cmd[:2]
        if not data.startswith(header):
            raise Error('Expected response header', header, data)
        if not data.endswith(END):
            raise Error('Expected END', END, data)
        res = data[len(header):-1]
        if self.print_cmd_res:
            print('  < Response:', res)
        return res

    def cmd_ref_bin(self, cmd, **kwargs):
        """Send command and retrieve binary response"""
        self._cmd(Header.reference, cmd, **kwargs)
        res = self.conn.recv()
        if self.print_cmd_bin_res:
            dumpdata.dumpdata('  < Response:', '{:02x}', res)
        return res

if __name__ == "__main__":
    print('test jvc command protocol class')
    try:
        with JVCConnection(print_all=True) as jvc:
            jvc.cmd_op(b'\0\0')
            jvc.cmd_ref(b'PW')
            jvc.cmd_ref_bin(b'PW')
    except jvc_network.Error as err:
        print('Error', err)
