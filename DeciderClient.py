#!/usr/bin/env python

import ciscotelnet
from scapy.sendrecv import sniff
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
from scapy.layers.inet import TCP, TCP_client
from scapy.sessions import TCPSession


class TelnetQuagga:

    def __init__(self, host, port):
        ciscotelnet.WAIT_TIMEOUT = 60
        self.router = ciscotelnet.CiscoTelnet(host=host, port=port, verbose=True)
        self.router.set_debuglevel(0)
        if self.router.login(final_mode=ciscotelnet.MODE_ENABLE, line_pass="zebra", enable_pass="zebra"):
            print("Successfull telnet authorization")
        else:
            print("Error of authorization")


if __name__ == '__main__':
    tq = TelnetQuagga(host="127.0.0.1", port=2605)
    print(tq.router.cmd("sh ip bgp"))
    print("")

    pkts = sniff(offline="invoke.pcap", filter='tcp port 8080', session=TCPSession)
    for pkt in pkts:
        if pkt[TCP].payload:
            pkt.show()
            print("==================================================")