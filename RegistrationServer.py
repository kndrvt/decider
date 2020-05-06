#!/usr/bin/python3

# Scapy
from scapy.all import *
from scapy.layers.http import HTTP, HTTPResponse, HTTPRequest

# HTTP
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from json import dumps

# System
from signal import signal, SIGINT
from os import kill, getpid
from time import sleep, time

rate = 1

class RegistrationServer(HTTPServer):

    def __init__(self, IP, Port, pause=10, timeout=10):
        HTTPServer.__init__(self, server_address=(IP, Port), RequestHandlerClass=HTTPRequestHandler)
        self.IP = IP
        self.Port = Port
        self.hosts = dict()
        self.pause = pause
        self.timeout = timeout
        self.lock = Lock()
        self.handler = None
        self.isRunning = False

    def start(self):
        self.isRunning = True
        self.handler = Thread(target=self.updateAll)
        self.handler.start()
        self.serve_forever()

    def finish(self):
        if self.isRunning:
            self.isRunning = False
            try:
                self.handler.join()
            except:
                pass
        self.server_close()

    def handle(self, data, address):
        shutdown = False
        http = HTTP(data)
        if http.name == 'HTTP 1':
            httpr = http.payload

            if httpr.name == 'HTTP Request':
                print()
                print("=== Request ===")
                print(httpr.summary(), address)

                payload = ""
                if httpr.Method.decode('ascii') == 'POST':
                    with self.lock:
                        self.hosts[address] = time()

                elif httpr.Method.decode('ascii') == 'GET':

                    if httpr.Path.decode('ascii') == "/Hosts":
                        with self.lock:
                            for host in self.hosts.keys():
                                payload += host + ' '

                    elif httpr.Path.decode('ascii') == "/Shutdown":
                        payload = str(time())
                        shutdown = True

                    else:
                        payload = str(time())

                else:
                    print(">>> Other request method")

                return bytes(HTTP() / HTTPResponse(Status_Code='200') / Raw(load=payload)), shutdown

            else:
                return bytes(HTTP / HTTPResponse(Status_Code='405')), shutdown

        else:
            return bytes(HTTP / HTTPResponse(Status_Code='400')), shutdown

    def updateAll(self):
        while self.isRunning:
            self.updateHosts()
            sleep(self.pause)
        kill(getpid(), SIGINT)

    def updateHosts(self):
        print()
        print("=== Hosts updating ===")

        try:
            with self.lock:
                ll = list(self.hosts.items())
                for host, htime in ll:
                    if time() - htime > self.timeout:
                        self.hosts.pop(host)
        except:
            print(">>> Uodate hosts exception")

        print(dumps(self.hosts, indent=2, sort_keys=True))


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def handle(self):
        self.data = self.request.recv(1024).strip()
        response, shutdown = self.server.handle(self.data, self.address_string())
        self.request.sendall(response)
        if shutdown:
            self.server.isRunning = False


def signalHandler(signum, frame):
    raise Exception("Shutdown")


if __name__ == '__main__':
    print()
    print('=== Registration server starting ===')
    signal(SIGINT, signalHandler)

    serverIP = '10.0.5.1'
    serverPort = 8080

    server = RegistrationServer(serverIP, serverPort, rate, 2)

    try:
        server.start()

    except:
        print(">>> Shutdown hosts exception")

    finally:
        print()
        print('=== Registration server stopping ===')
        server.finish()
