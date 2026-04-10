#!/usr/bin/env python3
"""
Broadcast Traffic Control - SDN Mininet Project
Topology: 1 switch, 4 hosts
Author: Shriya
"""

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

def create_topology():
    """Create a simple single-switch topology with 4 hosts"""

    net = Mininet(
        switch=OVSKernelSwitch,
        controller=RemoteController,
        link=TCLink,
        autoSetMacs=True
    )

    # Add remote Ryu controller
    info('*** Adding controller\n')
    c0 = net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6633
    )

    # Add single switch with OpenFlow 1.3
    info('*** Adding switch\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    # Add 4 hosts with static IPs and MACs
    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')

    # Add links (100Mbps, 1ms delay)
    info('*** Adding links\n')
    net.addLink(h1, s1, bw=100, delay='1ms')
    net.addLink(h2, s1, bw=100, delay='1ms')
    net.addLink(h3, s1, bw=100, delay='1ms')
    net.addLink(h4, s1, bw=100, delay='1ms')

    # Start network
    info('*** Starting network\n')
    net.start()

    # Force OpenFlow 1.3
    import os
    os.system('ovs-vsctl set bridge s1 protocols=OpenFlow13')

    info('*** Network ready. Use CLI to test.\n')
    info('*** Try: h1 ping h2, pingall, h1 ping -b 10.0.0.255\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
