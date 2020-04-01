#!/usr/bin/env python

# Quagga
from TelnetQuagga import TelnetQuagga

# Scapy
from scapy.all import *
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse

# TCP Server
from socketserver import TCPServer, BaseRequestHandler

# System
from signal import signal, SIGINT


class TCPRequestHandler(BaseRequestHandler):

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        # decider processing
        response = self.decide()
        # just send back the same data, but upper-cased
        self.request.sendall(response)

    def decide(self):

        pl = HTTP(self.data)
        if pl.name == 'HTTP 1':
            print("=================================")
            http = pl.payload
            print('Type:', http.name)

            if http.name == 'HTTP Request':
                print('Method:', http.Method.decode('ascii'))
                print('Host:', http.Host.decode('ascii'))
                print('Path:', http.Path.decode('ascii'))
                print('Payload:', http.payload.load.decode('ascii'))


            elif http.name == 'HTTP Response':
                print('Status code:', http.Status_Code.decode('ascii'))
                print('Payload:', http.payload.load.decode('ascii'))

            else:
                pass

            print("=================================")
            print()

        pkts = sniff(offline="invoke.pcap", filter='tcp port 8080', session=TCPSession)
        pl = pkts[5][TCP].payload
        return bytes(raw(pl))


def signalHandler(signum, frame):
    print()
    print('=== Stopping Client decider ===')
    exit()


if __name__ == '__main__':
    print()
    print('=== Starting Client decider ===')
    signal(SIGINT, signalHandler)

    # tq = TelnetQuagga(host="127.0.0.1", port=2605)
    # print(tq.cmd("sh ip bgp"))
    # print("")

    deciderIP = '10.0.8.51'
    clientIP = '10.0.7.1'
    # clientSession = TCP_client.tcplink(proto=HTTP, ip=clientIP, port=80)

    with TCPServer((deciderIP, 8080), TCPRequestHandler) as tcpd:
        print("Serving at port", 8080)
        tcpd.serve_forever()
