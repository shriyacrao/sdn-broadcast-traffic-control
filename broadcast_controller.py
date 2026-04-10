#!/usr/bin/env python3
"""
Broadcast Traffic Control - Ryu SDN Controller
Author: Shriya
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, arp, ether_types
from collections import defaultdict


class BroadcastController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    ARP_LIMIT = 10

    def __init__(self, *args, **kwargs):
        super(BroadcastController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.broadcast_count = defaultdict(int)
        self.unicast_count = defaultdict(int)
        self.arp_count = defaultdict(int)
        self.arp_blocked = set()
        self.logger.info("=" * 50)
        self.logger.info("  Broadcast Traffic Control - Started")
        self.logger.info("  ARP limit per host: %d", self.ARP_LIMIT)
        self.logger.info("=" * 50)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )]
        self.install_flow(datapath, 0, match, actions)
        self.logger.info("Switch %s connected - table-miss rule installed",
                         datapath.id)

    def install_flow(self, datapath, priority, match, actions,
                     idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            cookie=0,
            cookie_mask=0,
            table_id=0,
            command=ofproto.OFPFC_ADD,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
            priority=priority,
            buffer_id=ofproto.OFP_NO_BUFFER,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            flags=ofproto.OFPFF_SEND_FLOW_REM,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)

    def is_broadcast(self, dst_mac):
        return (dst_mac == 'ff:ff:ff:ff:ff:ff' or
                dst_mac.startswith('01:'))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        src_mac = eth.src
        dst_mac = eth.dst

        self.mac_to_port.setdefault(dpid, {})

        # MAC learning
        if src_mac not in self.mac_to_port[dpid]:
            self.mac_to_port[dpid][src_mac] = in_port
            self.logger.info("[LEARN] sw=%s MAC %s on port %s",
                             dpid, src_mac, in_port)

        # ARP flood detection
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt and self.is_broadcast(dst_mac):
            self.arp_count[src_mac] += 1
            self.logger.info("[ARP] src=%s count=%d/%d",
                             src_mac, self.arp_count[src_mac],
                             self.ARP_LIMIT)
            if (self.arp_count[src_mac] > self.ARP_LIMIT
                    and src_mac not in self.arp_blocked):
                self.arp_blocked.add(src_mac)
                self.logger.warning(
                    "[BLOCK] ARP flood from %s - DROP rule installed",
                    src_mac)
                match = parser.OFPMatch(
                    eth_src=src_mac,
                    eth_dst='ff:ff:ff:ff:ff:ff'
                )
                self.install_flow(datapath, 20, match, [],
                                  idle_timeout=60)
                return

        # Forwarding decision
        if self.is_broadcast(dst_mac):
            out_port = ofproto.OFPP_FLOOD
            self.broadcast_count[dpid] += 1
            self.logger.info(
                "[BROADCAST] sw=%s src=%s -> FLOOD (total=%d)",
                dpid, src_mac, self.broadcast_count[dpid])

        elif dst_mac in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst_mac]
            self.unicast_count[dpid] += 1

            # Install selective unicast flow rule
            match = parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst_mac,
                eth_src=src_mac
            )
            self.install_flow(
                datapath, 10, match,
                [parser.OFPActionOutput(out_port)],
                idle_timeout=30,
                hard_timeout=120
            )
            self.logger.info(
                "[UNICAST] sw=%s %s->%s port=%s "
                "broadcast=%d unicast=%d",
                dpid, src_mac, dst_mac, out_port,
                self.broadcast_count[dpid],
                self.unicast_count[dpid])
        else:
            out_port = ofproto.OFPP_FLOOD
            self.broadcast_count[dpid] += 1
            self.logger.info("[UNKNOWN] sw=%s dst=%s -> FLOOD",
                             dpid, dst_mac)

        # Send packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=[parser.OFPActionOutput(out_port)],
            data=data
        )
        datapath.send_msg(out)
