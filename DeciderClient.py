#!/usr/bin/env python

# Quagga
import ciscotelnet

# Scapy
from scapy.all import *
from scapy.layers.http import *


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
    # tq = TelnetQuagga(host="127.0.0.1", port=2605)
    # print(tq.router.cmd("sh ip bgp"))
    # print("")

    pkts = sniff(offline="invoke.pcap", filter='tcp port 8080', session=TCPSession)
    for pkt in pkts:
        http = pkt[TCP].payload
        if http:
            print("=================================")
            httpr = http.payload
            print('Type:', httpr.name)

            if httpr.name == 'HTTP Request':
                print('Method:', httpr.Method.decode('ascii'))
                print('Host:', httpr.Host.decode('ascii'))
                print('Path:', httpr.Path.decode('ascii'))
                print('Payload:', httpr.payload.load.decode('ascii'))

            elif httpr.name == 'HTTP Response':
                print('Status code:', httpr.Status_Code.decode('ascii'))
                print('Payload:', httpr.payload.load.decode('ascii'))

            else:
                pass

            print("=================================")
            print()
