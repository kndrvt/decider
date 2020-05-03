#!/usr/bin/python3

# HTTP
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from json import dumps

# System
from signal import signal, SIGINT
from time import sleep, clock


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
        self.isRunning = False
        self.handler.join()
        self.server_close()

    def updateAll(self):
        while self.isRunning:
            self.updateHosts()
            sleep(self.pause)
        exit(0)

    def updateHosts(self):
        print()
        print("=== Hosts updating ===")

        with self.lock:
            for host, time in self.hosts.items():
                if clock() - time > self.timeout:
                    self.hosts.pop(host)

        print(dumps(self.hosts, indent=2, sort_keys=True))


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        with self.server.lock:
            self.server.hosts[self.address_string()] = clock()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        with self.server.lock:
            for host in self.server.hosts.keys():
                self.wfile.write(bytes(host, 'ascii'))
                self.wfile.write(bytes(' ', 'ascii'))


def signalHandler(signum, frame):
    raise Exception("Shutdown")


if __name__ == '__main__':
    print()
    print('=== Registration server starting ===')
    signal(SIGINT, signalHandler)

    serverIP = '10.0.6.1'
    serverPort = 8080

    server = RegistrationServer(serverIP, serverPort, 2, 60)

    try:
        server.start()

    except:
        pass

    finally:
        print()
        print('=== Registration server stopping ===')
        server.finish()
