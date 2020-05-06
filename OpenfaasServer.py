#!/usr/bin/python3

# Scapy
from scapy.all import *
from scapy.layers.http import HTTP, HTTPResponse

# HTTP
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from requests import get, post
from json import dumps

# System
from signal import signal, SIGINT
from os import kill, getpid
from time import sleep, time
from collections import defaultdict
import sys

rate = 1

class OpenfaasServer(HTTPServer):

    def __init__(self, IP, Port, faasIP, faasPort, regServerIP, regServerPort, pause=10,
                 duration=20):
        HTTPServer.__init__(self, server_address=(IP, Port), RequestHandlerClass=HTTPRequestHandler)

        self.IP = IP
        self.Port = Port
        self.faasIP = faasIP
        self.faasPort = faasPort
        self.regServerIP = regServerIP
        self.regServerPort = regServerPort
        self.pause = pause  # seconds
        self.lock = Lock()
        self.faasMetrics = defaultdict(dict)
        self.duration = duration  # seconds
        self.handler = None
        self.isRunning = False

    def __del__(self):
        self.handler.join()

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

    def handle(self, data):
        shutdown = False
        http = HTTP(data)
        if http.name == 'HTTP 1':
            httpr = http.payload

            if httpr.name == 'HTTP Request':
                print()
                print("=== Request ===")
                print(httpr.summary())

                payload = str(time())
                if httpr.Path.decode('ascii') == "/Metrics":
                    with self.lock:
                        payload = dumps(dict(self.faasMetrics))

                elif httpr.Path.decode('ascii') == "/Shutdown":
                    shutdown = True

                elif httpr.Path.decode('ascii') == "/Run":
                    pass

                else:
                    print("Bad Path")

                return bytes(HTTP() / HTTPResponse(Status_Code='200') / Raw(
                    load=payload)), shutdown
            else:
                return bytes(HTTP / HTTPResponse(Status_Code='405')), shutdown

        else:
            return bytes(HTTP / HTTPResponse(Status_Code='400')), shutdown

    def updateAll(self):
        while self.isRunning:
            self.updateRegistration()
            self.updateFaasMetrics()
            sleep(self.pause)
        kill(getpid(), SIGINT)

    def updateRegistration(self):
        print()
        print("=== Reqistartion updating ===")

        try:
            response = post("http://" + self.regServerIP + ":" + str(self.regServerPort) + "/Registration")
        except:
            print(">>> Reqistration hasn't been updated")

    def updateFaasMetrics(self):
        print()
        print("=== Faas metrics updating ===")

        with self.lock:
            self.faasMetrics.clear()
            URL = "http://" + self.faasIP + ":" + str(self.faasPort) + "/api/v1/"

            parameters = {
                # function invocation rate
                'inv_rate': "query?query=rate(gateway_function_invocation_total{{code=\"200\"}}[{0}s])",
                # function replica count
                'rep_count': "query?query=gateway_service_count",
                # average function execution time
                'exec_time': "query?query=(rate(gateway_functions_seconds_sum[{0}s])\
               /rate(gateway_functions_seconds_count[{0}s]))"
            }

            for name, parameter in parameters.items():
                global response
                try:
                    response = get(URL + parameter.format(self.duration))
                except:
                    print(">>>", name, "metrics haven't been updated")
                    continue
                # print(dumps(response.json(), indent=2, sort_keys=True))
                if response.json()["status"] == "success":
                    for result in response.json()['data']['result']:
                        value = result['value'][1]
                        if value != '0' and value != 'NaN':
                            self.faasMetrics[result['metric']['function_name']][name] = float(value)
                        else:
                            self.faasMetrics[result['metric']['function_name']][name] = float(0)

                else:
                    print("Response status differs from \'success\'")

            print(dumps(self.faasMetrics, indent=2, sort_keys=True))


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def handle(self):
        self.data = self.request.recv(1024).strip()
        response, shutdown = self.server.handle(self.data)
        self.request.sendall(response)
        if shutdown:
            self.server.isRunning = False


def signalHandler(signum, frame):
    raise Exception("Shutdown")


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print('Usage: sudo python3 OpenfaasServer.py <IP address>')
        exit()

    print()
    print('=== Openfaas server starting ===')
    signal(SIGINT, signalHandler)

    serverIP = sys.argv[1]
    serverPort = 8888
    faasIP = sys.argv[1]
    faasPort = 9090
    regServerIP = '10.0.5.1'
    regServerPort = 8080

    server = OpenfaasServer(serverIP, serverPort, faasIP, faasPort, regServerIP, regServerPort, 0.25)

    try:
        server.start()

    except:
        pass

    finally:
        print()
        print('=== Openfaas server stopping ===')
        server.finish()

    print("=== Sleeping ===")
    os.system("sudo iptables -A INPUT -p icmp --icmp-type echo-request -j REJECT")
    sleep(10)
    os.system("sudo iptables -D INPUT -p icmp --icmp-type echo-request -j REJECT")

    server = OpenfaasServer(serverIP, serverPort, faasIP, faasPort, regServerIP, regServerPort, rate)

    try:
        server.start()

    except:
        pass

    finally:
        print()
        print('=== Openfaas server stopping ===')
        server.finish()
