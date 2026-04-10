# SDN Broadcast Traffic Control
SDN Mininet project - Broadcast Traffic Control using Ryu OpenFlow controller

## Problem Statement
In traditional networks, broadcast traffic floods all ports, causing unnecessary 
bandwidth consumption and network congestion. This project implements an 
SDN-based solution using Mininet and Ryu OpenFlow controller to detect, 
limit, and control broadcast traffic by installing selective unicast 
forwarding rules.

## Objectives
- Detect broadcast packets at the controller
- Limit unnecessary flooding using MAC learning
- Install selective unicast flow rules for known destinations
- Monitor and log broadcast vs unicast traffic statistics
- Detect and block ARP flooding attacks

## Topology
h1 (10.0.0.1) ---|
h2 (10.0.0.2) ---| s1 (OpenFlow Switch)
h3 (10.0.0.3) ---|
h4 (10.0.0.4) ---|
- 1 OpenFlow switch (OVS) running OpenFlow 1.3
- 4 hosts with static IPs and MACs
- Link speed: 100Mbps, delay: 1ms

## SDN Logic
### Controller Behavior
1. **Table-miss rule** — sends unknown packets to controller (priority=0)
2. **MAC Learning** — learns source MAC to port mapping
3. **Broadcast Detection** — detects ff:ff:ff:ff:ff:ff destination
4. **Selective Forwarding** — installs unicast rules for known MACs (priority=10)
5. **ARP Flood Detection** — blocks hosts sending more than 10 ARP broadcasts (priority=20)

### Flow Rule Design
| Priority | Match | Action | Timeout |
|----------|-------|---------|---------|
| 0 | any | send to controller | permanent |
| 10 | in_port + src_mac + dst_mac | output to specific port | idle=30s |
| 20 | src_mac + dst=broadcast | drop | idle=60s |

## Setup & Installation

### Requirements
- VirtualBox with Ubuntu 20.04
- Mininet 2.3.1
- Ryu 4.34
- Python 3.8

### Installation
```bash
# Install Mininet
sudo apt install mininet -y

# Install Ryu
pip3 install ryu
pip3 install eventlet==0.30.2

# Clone this repo
git clone https://github.com/shriyacrao/sdn-broadcast-traffic-control
cd sdn-broadcast-traffic-control
```

## Execution Steps

### Terminal 1 — Start Ryu Controller
```bash
ryu-manager broadcast_controller.py
```

### Terminal 2 — Start Mininet Topology
```bash
sudo python3 topology.py
```

### Run Tests
```bash
# Test 1 - Normal forwarding
mininet> pingall

# Check flow table
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1

# Test 2 - Broadcast traffic
mininet> h1 ping -b -c 5 10.0.0.255

# Test 3 - Throughput
mininet> iperf h1 h2

# Wireshark capture
mininet> h1 wireshark &
mininet> h1 ping -c 5 h2
```

## Test Scenarios

### Scenario 1 — Normal Unicast Forwarding
- Run `pingall` → all hosts reach each other
- Controller learns MAC addresses
- Installs selective unicast flow rules
- **Result:** 0% packet loss, 12/12 received

### Scenario 2 — Broadcast Traffic Detection
- Run `h1 ping -b -c 5 10.0.0.255`
- Controller detects broadcast packets
- Logs BROADCAST events with count
- **Result:** Broadcast detected, selective rules prevent unnecessary flooding

## Expected Output

### pingall
h1 -> h2 h3 h4
h2 -> h1 h3 h4
h3 -> h1 h2 h4
h4 -> h1 h2 h3
*** Results: 0% dropped (12/12 received)

### Flow Table
priority=10, in_port=s1-eth1, dl_src=00:00:00:00:00:01,
dl_dst=00:00:00:00:00:02, actions=output:s1-eth2

### iperf
*** Results: ['84.9 Mbits/sec', '100.8 Mbits/sec']

## Performance Analysis
| Metric | Value |
|--------|-------|
| Latency (ping) | ~1ms (matches 1ms link delay) |
| Throughput (iperf) | ~85-100 Mbits/sec |
| Flow rules installed | 12 unicast + 1 table-miss |
| Broadcast packets detected | Logged with count |

## Proof of Execution
Screenshots are in the `/screenshots` folder:

| Screenshot | Description |
|------------|-------------|
| controller_started | Ryu controller startup |
| topology_started | Mininet topology creation |
| pingall_success | All hosts reachable, 0% drop |
| ryu_unicast_learning | MAC learning and unicast forwarding logs |
| flow_table | Flow rules installed after pingall |
| broadcast_ping | Broadcast ping test |
| ryu_broadcast_detected | Controller detecting broadcast packets |
| iperf_result | Throughput measurement |
| flow_table_stats | Flow table with packet counts |
| wireshark_capture | Packet capture showing ICMP and ARP |

## References
1. Mininet Documentation — http://mininet.org
2. Ryu SDN Framework — https://ryu-sdn.org
3. OpenFlow Specification 1.3 — https://opennetworking.org
4. B. Lantz, B. Heller, N. McKeown, "A Network in a Laptop: Rapid Prototyping for Software-Defined Networks", ACM HotNets 2010
5. OpenFlow Switch Specification — https://opennetworking.org/wp-content/uploads/2014/10/openflow-spec-v1.3.0.pdf
