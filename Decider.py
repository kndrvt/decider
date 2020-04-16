#!/usr/bin/env python

# Scapy
from scapy.all import *
from scapy.layers.http import HTTP, HTTPResponse

# HTTP
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from requests import get, post
from json import loads, dumps

# System
from signal import signal, SIGINT
from time import clock, sleep


class Decider(HTTPServer):

    def __init__(self, IP, Port, faasPort, hosts, maxrtt=5000, maxhop=64, bufsize=3):
        HTTPServer.__init__(self, server_address=(IP, Port), RequestHandlerClass=HTTPRequestHandler)
        self.IP = IP
        self.Port = Port
        self.faasPort = faasPort
        self.lock = Lock()
        self.hosts = hosts
        self.maxrtt = maxrtt
        self.maxhop = maxhop
        self.rtt = defaultdict(list)
        self.rttav = defaultdict(float)
        self.hop = defaultdict(list)
        self.hopav = defaultdict(float)
        self.bufsize = bufsize
        self.faasMetrics = defaultdict(dict)
        self.bestHosts = defaultdict(str)

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
                # print("=================================")
                # print('Type:', httpr.name)
                # print('Method:', httpr.Method.decode('ascii'))
                # print('Host:', httpr.Host.decode('ascii'))
                # print('Path:', httpr.Path.decode('ascii'))
                # print('Payload:', httpr.payload.load.decode('ascii'))
                # print("=================================")

                global response
                s = httpr.Path.decode('ascii')
                n = s.rindex("/")
                faasIP = self.decide(s[n + 1:])

                print("=== Redirection ===")
                print(http.summary(), " --> ", faasIP)

                if faasIP:
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
                            load=response.content.decode('ascii')))
                    else:
                        return bytes(HTTP / HTTPResponse(Status_Code='405'))
                else:
                    return bytes(HTTP / HTTPResponse(Status_Code='400'))
            else:
                return bytes(HTTP / HTTPResponse(Status_Code='400'))
        else:
            return bytes(HTTP / HTTPResponse(Status_Code='400'))

    def decide(self, function) -> str:
        with self.lock:
            return self.bestHosts[function]

    def updateAll(self):
        while True:
            self.updateHosts()
            self.updateNetworkMetrics()
            self.updateFaasMetrics()
            self.updateBestHosts()
            sleep(10)

    def updateHosts(self):
        print()
        print("=== Hosts updating ===")
        pass

    def updateNetworkMetrics(self):
        print()
        print("=== Network metrics updating ===")

        maxMetrics = [0, 0]
        for targetIP in self.hosts:
            sum_rtt = 0
            sum_hop = 0
            n = 1
            for i in range(n):
                rtt, hop = self.ping(targetIP)
                sum_rtt += rtt
                sum_hop += hop

            if len(self.rtt[targetIP]) >= self.bufsize:
                self.rtt[targetIP].pop(0)
                self.hop[targetIP].pop(0)
            self.rtt[targetIP].append(sum_rtt / n)
            self.hop[targetIP].append(sum_hop / n)

            sum = 0
            for rtt in self.rtt[targetIP]:
                sum += rtt
            self.rttav[targetIP] = sum / len(self.rtt[targetIP])
            if self.rttav[targetIP] > maxMetrics[0]:
                maxMetrics[0] = self.rttav[targetIP]

            sum = 0
            for hop in self.hop[targetIP]:
                sum += hop
            self.hopav[targetIP] = sum / len(self.hop[targetIP])
            if self.hopav[targetIP] > maxMetrics[1]:
                maxMetrics[1] = self.hopav[targetIP]

        # normalization
        for host, metric in self.rttav.items():
            if maxMetrics[0] > 0:
                self.rttav[host] /= maxMetrics[0]
            else:
                self.rttav[host] = 1

        for host, metric in self.hopav.items():
            if maxMetrics[1] > 0:
                self.hopav[host] /= maxMetrics[1]
            else:
                self.hopav[host] = 1

        print(dumps(self.rttav, indent=2, sort_keys=True))
        print(dumps(self.hopav, indent=2, sort_keys=True))

    def ping(self, targetIP):
        start = clock()
        ans, unans = sr(IP(dst=targetIP, ttl=64) / ICMP(), timeout=10)
        if ans:
            return 1000 * (clock() - start), 64 - ans[0][1][IP].ttl + 1
        else:
            return self.maxrtt, self.maxhop

    def updateFaasMetrics(self):
        print()
        print("=== Faas metrics updating ===")

        maxMetrics = dict()
        for host in self.hosts:
            response = get("http://" + host + ":" + str(self.faasPort))
            faasmetrics = loads(response.content.decode('ascii'))

            # print("=======================")
            # print(dumps(faasmetrics, indent=2, sort_keys=True))

            for function, metrics in faasmetrics.items():
                if not maxMetrics.get(function):
                    maxMetrics[function] = [0, 0, 0]
                for i in range(3):
                    if metrics[i] > maxMetrics[function][i]:
                        maxMetrics[function][i] = metrics[i]
                with self.lock:
                    self.faasMetrics[function][host] = metrics

        # normalization
        for function, hosts in self.faasMetrics.items():
            for host, metrics in hosts.items():
                for i in range(3):
                    if maxMetrics[function][i] > 0:
                        self.faasMetrics[function][host][i] /= maxMetrics[function][i]

        # print("=======================")
        print(dumps(dict(self.faasMetrics), indent=2, sort_keys=True))

    def updateBestHosts(self):
        print()
        print("=== The best hosts updating ===")

        for function in self.faasMetrics.keys():
            targetValues = dict()
            for host in self.hosts:
                targetValues[self.targetFunction(function, host)] = host
            print(dumps(targetValues, indent=2, sort_keys=True))
            value = min(targetValues.keys())
            self.bestHosts[function] = targetValues[value]

        print(dumps(dict(self.bestHosts), indent=2, sort_keys=True))

    def targetFunction(self, function, host):
        return self.faasMetrics[function][host][0] + \
               1 - self.faasMetrics[function][host][1] + \
               self.faasMetrics[function][host][2] + \
               self.rttav[host] + \
               self.hopav[host]


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def handle(self):
        self.data = self.request.recv(1024).strip()
        response = self.server.handle(self.data)
        self.request.sendall(response)


def signalHandler(signum, frame):
    print()
    print('=== Stopping Client decider ===')
    exit()


if __name__ == '__main__':
    print()
    print('=== Starting Client decider ===')
    signal(SIGINT, signalHandler)

    deciderIP = '10.0.8.51'
    deciderPort = 8080
    faasPort = 8888
    hosts = ['10.0.8.52']

    decider = Decider(deciderIP, deciderPort, faasPort, hosts)
    decider.start()
