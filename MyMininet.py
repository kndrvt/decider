import os
import time
from mininet.net import Mininet
from mininet.topo import Topo, SingleSwitchTopo
from mininet.node import OVSSwitch, RemoteController, Node
from mininet.cli import CLI
from mininet.link import OVSLink, Intf
from mininet.log import setLogLevel, info

class LinuxRouter(Node):
    """A Node with IP forwarding enabled."""

    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

class NetworkTopo(Topo):
    """Two Linux Routers (Quagga) are each connected to a host."""

    def build(self, **_opts):
        info("### Adding routers and hosts \n")
        r1 = self.addNode('r1', cls=LinuxRouter)
        # r2 = self.addNode('r2', cls=LinuxRouter)
        h1 = self.addHost('h1', ip='10.0.7.5/24')
        h2 = self.addHost('h2', ip='10.0.7.6/24')

        info("### Add links")
        l1 = self.addLink(h1, r1)
        l2 = self.addLink(h2, r1)

def SetQuagga(Router):
    """Start zebra and bgpd."""

    # Router.cmd('/usr/local/sbin/zebra -f conf/%s-zebra.conf -d -i /tmp/%s-zebra.pid -z /tmp/%s-zebra.api > logs/%s-zebra-stdout 2>&1'
    #            % (Router.name, Router.name, Router.name, Router.name))
    # Router.waitOutput()
    #
    # Router.cmd('/usr/local/sbin/ospfd -f conf/%s-ospfd.conf -d -i /tmp/%s-ospfd.pid -z /tmp/%s-zebra.api > logs/%s-ospfd-stdout 2>&1'
    #     % (Router.name, Router.name, Router.name, Router.name), shell=True)
    # Router.waitOutput()

    Router.cmd('/usr/local/sbin/zebra -f conf/zebra.conf -d -i /tmp/zebra.pid -z /tmp/zebra.api')
    Router.waitOutput()

    Router.cmd('/usr/local/sbin/bgpd -f conf/bgpd.conf -d -i /tmp/bgpd.pid -z /tmp/bgpd.api')
    Router.waitOutput()

def run():
    info("### Create a network \n")
    # net = Mininet(topo=NetworkTopo(), switch=OVSSwitch, link=OVSLink, controller=RemoteController)
    net = Mininet(topo=NetworkTopo(), controller=None)
    # net.controller = RemoteController('c0', ip='127.0.0.1', port=6653)

    info("### Start network \n")
    net.start()

    info("### Getting nodes \n")
    h1 = net.getNodeByName('h1')
    h2 = net.getNodeByName('h2')
    r1 = net.getNodeByName('r1')
    # r2 = net.getNodeByName('r2')

    # info("### Add external interfaces \n")
    # intf = Intf(name='enp0s3', node=r1, ip='10.0.7.4/24')
    #
    info("### Starting Quagga \n")
    SetQuagga(r1)
    # SetQuagga(r2)

    # info("### Leasing DHCP addresses \n")
    # h1.cmd("dhclient -r && dhclient")
    # h2.cmd("dhclient -r && dhclient")

    CLI(net)

    info("### Stoping network \n")
    net.stop()

    os.system('killall -9 zebra bgpd')


def main():
    setLogLevel('info')
    run()


if __name__ == '__main__':
    main()