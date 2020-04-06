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
        r1 = self.addNode('r1', cls=LinuxRouter, ip='10.0.7.51/24')
        r2 = self.addNode('r2', cls=LinuxRouter, ip='10.0.8.52/24')

        h1 = self.addHost('h1', ip='10.0.7.1/24', defaultRoute='via 10.0.7.51')
        # h2 = self.addHost('h2', ip='10.0.9.1/24', defaultRoute='via 10.0.9.52')

        info("### Add links")
        l1 = self.addLink(h1, r1, intfName1='h1-eth2', intfName2='r1-eth2')
        # l2 = self.addLink(h2, r2, intfName1='h2-eth1', intfName2='r2-eth1')
        l3 = self.addLink(r1, r2, intfName1='r1-eth1', intfName2='r2-eth1')

def SetQuagga(Router):
    """Start zebra and bgpd."""

    # Router.cmd('/usr/local/sbin/zebra -f conf/%s-zebra.conf -d -i /tmp/%s-zebra.pid -z /tmp/%s-zebra.api > logs/%s-zebra-stdout 2>&1'
    #            % (Router.name, Router.name, Router.name, Router.name))
    # Router.waitOutput()
    #
    # Router.cmd('/usr/local/sbin/ospfd -f conf/%s-ospfd.conf -d -i /tmp/%s-ospfd.pid -z /tmp/%s-zebra.api > logs/%s-ospfd-stdout 2>&1'
    #     % (Router.name, Router.name, Router.name, Router.name), shell=True)
    # Router.waitOutput()

    Router.cmd('sudo /usr/local/sbin/zebra -f conf/%s-zebra.conf -d -i /tmp/%s-zebra.pid -z /tmp/%s-zebra.api'
               % (Router.name, Router.name, Router.name), shell=True)
    Router.waitOutput()

    Router.cmd('sudo /usr/local/sbin/bgpd -f conf/%s-bgpd.conf -d -i /tmp/%s-bgpd.pid -z /tmp/%s-bgpd.api'
               % (Router.name, Router.name, Router.name), shell=True)
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
    # h2 = net.getNodeByName('h2')
    r1 = net.getNodeByName('r1')
    r2 = net.getNodeByName('r2')

    info("### Add external interfaces \n")
    intf = Intf(name='enp0s8', node=r2, ip='10.0.9.52/24')

    info("### Starting Quagga \n")
    SetQuagga(r1)
    SetQuagga(r2)

    # info("### Starting Wireshark \n")
    # r1.cmd("wireshark &")
    # r1.cmd("sleep 3")

    # info("### Starting Decider \n")
    # r1.cmd("xterm &")
    # h1.cmd("xterm &")
    # h1.cmd("sleep 5")
    # h1.cmd("echo kek | faas-cli --gateway 10.0.7.51 invoke figlet")


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