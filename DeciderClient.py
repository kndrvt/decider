#!/usr/bin/env python

# Quagga
from TelnetQuagga import TelnetQuagga

# Scapy
from scapy.all import *
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse, TCP_client
from requests import get, post

# TCP Server
from socketserver import TCPServer, BaseRequestHandler

# System
from signal import signal, SIGINT


class DeciderClient(TCPServer):

    def __init__(self, IP, telnetquagga, faasPort):
        TCPServer.__init__(self, server_address=(IP, faasPort), RequestHandlerClass=TCPRequestHandler)
        self.IP = IP
        self.telnetquagga = telnetquagga
        self.faasPort = faasPort

    def start(self):
        print("Serving at port", self.faasPort)
        self.serve_forever()

    def handle(self, data):
        http = HTTP(data)
        if http.name == 'HTTP 1':
            httpr = http.payload

            if httpr.name == 'HTTP Request':
                # print("=================================")
                # print('Type:', httpr.name)
                # print('Method:', httpr.Method.decode('ascii'))
                # print('Host:', httpr.Host.decode('ascii'))
                # print('Path:', httpr.Path.decode('ascii'))
                # print('Payload:', httpr.payload.load.decode('ascii'))
                # print("=================================")

                global response
                faasIP = self.decide(http)
                if httpr.Method.decode('ascii') == 'POST':
                    response = post(url="http://" + faasIP + ':' + str(self.faasPort) + httpr.Path.decode('ascii'),
                                    data=httpr.payload.load.decode('ascii'))
                elif http.Method.decode('ascii') == 'GET':
                    response = get(url="http://" + faasIP + ':' + str(self.faasPort) + httpr.Path.decode('ascii'),
                                   data=httpr.payload.load.decode('ascii'))
                else:
                    print("Other request method")
                    response = None

                # print("=================================")
                # print(HTTP() / HTTPResponse(Status_Code=str(response.status_code)) / Raw(
                #     load=response.content.decode(response.encoding)))
                # print("=================================")

                if response:
                    return bytes(HTTP() / HTTPResponse(Status_Code=str(response.status_code)) / Raw(
                        load=response.content.decode(response.encoding)))
                else:
                    return bytes(HTTP / HTTPResponse(Status_Code='405'))
            else:
                return bytes(HTTP / HTTPResponse(Status_Code='400'))
        else:
            bytes(HTTP / HTTPResponse(Status_Code='400'))

    def decide(self, http) -> str:
        return '10.0.9.1'


class TCPRequestHandler(BaseRequestHandler):

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()

        # request handling
        response = self.server.handle(self.data)

        # send response
        self.request.sendall(response)


def signalHandler(signum, frame):
    print()
    print('=== Stopping Client decider ===')
    exit()


if __name__ == '__main__':
    print()
    print('=== Starting Client decider ===')
    signal(SIGINT, signalHandler)

    tq = TelnetQuagga(host="127.0.0.1", port=2605)
    deciderIP = '10.0.8.52'
    faasPort = 8080

    deciderClient = DeciderClient(deciderIP, tq, faasPort)
    deciderClient.start()
