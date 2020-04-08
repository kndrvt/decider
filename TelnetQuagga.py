#!/usr/bin/env python

import ciscotelnet


class TelnetQuagga:

    def __init__(self, host, port):
        ciscotelnet.WAIT_TIMEOUT = 60
        self.router = ciscotelnet.CiscoTelnet(host=host, port=port, verbose=True)
        self.router.set_debuglevel(0)
        if self.router.login(final_mode=ciscotelnet.MODE_ENABLE, line_pass="zebra", enable_pass="zebra"):
            print("Successfull telnet authorization")
        else:
            print("Error of authorization")

    def cmd(self, command):
        return self.router.cmd(command)
