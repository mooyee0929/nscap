# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import in_proto


FILTER_TABLE_1 = 1
FILTER_TABLE_2 = 2
FORWARD_TABLE = 10

class ExampleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ExampleSwitch13, self).__init__(*args, **kwargs)
        # initialize mac address table.
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        
        print("======================================")
        print("|       Table-miss Flow Entry        |")
        print("======================================")
        print("datapath => ",datapath)
        print("priority => ",1)
        print("match => ",match)
        print("actions => ",actions)
        print("======================================")
        print("..")
        print("..")

        self.add_flow(datapath, 0, match, actions)

        #adding default tables/rules in the startup
        self.add_default_table(datapath)
        self.add_filter_table1(datapath)
        self.add_filter_table2(datapath)
        self.apply_filter_table_rules1(datapath)
        self.apply_filter_table_rules2(datapath)
        self.apply_filter_table_rules3(datapath)


    def add_flow(self, datapath, priority, match, actions, buffer_id = None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, table_id=FORWARD_TABLE,
                                    match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, table_id=FORWARD_TABLE,
                                    instructions=inst)
        datapath.send_msg(mod)

    def add_default_table(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(FILTER_TABLE_1)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=0, instructions=inst)
        datapath.send_msg(mod)

    def add_filter_table1(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_1, 
                                priority=1, instructions=inst)
        datapath.send_msg(mod)
        
    def apply_filter_table_rules1(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(FILTER_TABLE_2)]
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=in_proto.IPPROTO_ICMP)
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_1,
                                priority=10000, match=match, instructions=inst)
        datapath.send_msg(mod)

    def add_filter_table2(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2, 
                                priority=1, instructions=inst)
        datapath.send_msg(mod)


    def apply_filter_table_rules2(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(in_port = 3)
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2,
                                priority=10000, match=match)
        datapath.send_msg(mod)

    def apply_filter_table_rules3(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(in_port = 4)
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2,
                                priority=10000, match=match)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # get Datapath ID to identify OpenFlow switches.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        print("======================================")
        print("add switch",dpid,"to mac_to_port table")
        print("======================================")
        print("..")
        print("..")

        # analyse the received packets using the packet library.
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src

        # get the received port number from packet_in message.
        in_port = msg.match['in_port']
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        print("======================================")
        print("|             Packt in Event         |")
        print("======================================")
        print("dpid => ",dpid)
        print("src => ",src)
        print("dst => ",dst)
        print("in_port => ",in_port)
        print("======================================")
        print("..")
        print("..")

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port
        print("======================================")
        print("|          mac_to_port Table         |")
        print("======================================")
        print(self.mac_to_port)
        print("======================================")
        print("..")
        print("..")


        # if the destination mac address is already learned,
        # decide which port to output the packet, otherwise FLOOD.
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # construct action list.
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time.
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                print("======================================")
                print("|            Add Flow Entry          |")
                print("======================================")
                print("datapath => ",datapath)
                print("priority => ",1)
                print("match => ",match)
                print("actions => ",actions)
                print("buffer_id => ",msg.buffer_id)
                print("======================================")
                print("..")
                print("..")
                self.add_flow(datapath, 1, match, actions,msg.buffer_id)
            else:
                print("======================================")
                print("|            Add Flow Entry          |")
                print("======================================")
                print("datapath => ",datapath)
                print("priority => ",1)
                print("match => ",match)
                print("actions => ",actions)
                print("======================================")
                print("..")
                print("..")
                self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        # construct packet_out message and send it.
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=in_port, actions=actions,
                                  data=data)
        datapath.send_msg(out)