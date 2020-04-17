#!/usr/bin/env python

# Scapy
from scapy.all import *
from scapy.layers.http import HTTP, HTTPResponse

# HTTP
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from requests import get
from json import dumps

# System
from signal import signal, SIGINT
from time import sleep
from collections import defaultdict


class OpenfaasServer(HTTPServer):

    def __init__(self, IP, Port, faasIP, faasPort, pause=10,
                 duration=20):
        HTTPServer.__init__(self, server_address=(IP, Port), RequestHandlerClass=HTTPRequestHandler)

        self.IP = IP
        self.Port = Port
        self.faasIP = faasIP
        self.faasPort = faasPort
        self.pause = pause  # seconds
        self.lock = Lock()
        self.faasMetrics = defaultdict(dict)
        self.duration = duration  # seconds
        self.handler = None

    def __del__(self):
        self.handler.join()

    def start(self):
        self.handler = Thread(target=self.updateAll)
        self.handler.start()
        self.serve_forever()

    def handle(self, data):
        http = HTTP(data)
        if http.name == 'HTTP 1':
            httpr = http.payload

            if httpr.name == 'HTTP Request':
                print()
                print("=== Request ===")
                print(httpr.summary())

                with self.lock:
                    payload = dumps(dict(self.faasMetrics))

                return bytes(HTTP() / HTTPResponse(Status_Code='200') / Raw(
                    load=payload))
            else:
                return bytes(HTTP / HTTPResponse(Status_Code='405'))

        else:
            return bytes(HTTP / HTTPResponse(Status_Code='400'))

    def updateAll(self):
        while True:
            self.updateFaasMetrics()
            sleep(self.pause)

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
        response = self.server.handle(self.data)
        self.request.sendall(response)


def signalHandler(signum, frame):
    print()
    print('=== Openfaas server stopping ===')
    exit()


if __name__ == '__main__':
    print()
    print('=== Openfaas server starting ===')
    signal(SIGINT, signalHandler)

    serverIP = '10.0.9.1'
    serverPort = 8888
    faasIP = '10.0.9.1'
    faasPort = 9090

    server = OpenfaasServer(serverIP, serverPort, faasIP, faasPort, 5)
    server.start()
