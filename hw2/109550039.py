from setting import get_hosts, get_switches, get_links, get_ip, get_mac


class host:
    def __init__(self, name, ip, mac):
        self.name = name
        self.ip = ip
        self.mac = mac 
        self.port_to = None 
        self.arp_table = dict() # maps IP addresses to MAC addresses
    def add(self, node):
        self.port_to = node
    def show_table(self):
        # display ARP table entries for this host
        print('---------------',self.name,':')
        for entry in self.arp_table:
            print(entry,':',self.arp_table[entry])
    def clear(self):
        # clear ARP table entries for this host
        self.arp_table.clear()
    def update_arp(self, ip,mac):
        # update ARP table with a new entry
        self.arp_table[ip] = mac
    def handle_packet(self, dst_ip,src_ip, from_list, dst_mac, src_mac): # handle incoming packets
        if(self.ip == dst_ip):
            self.update_arp (src_ip,src_mac)
            return self.mac
        else:
            return 0
    def ping(self, dst_ip): # handle a ping request
        from_list = list()
        if(dst_ip in self.arp_table.keys()):
            self.send(dst_ip,self.ip,from_list,self.arp_table[dst_ip],self.mac) #icmp
        else:
            dst_mac = self.send(dst_ip,self.ip, from_list, 'ffff', self.mac) #arp
            self.update_arp(dst_ip,dst_mac)
            self.send(dst_ip,self.ip, from_list, self.arp_table[dst_ip],self.mac) #icmp
    def send(self, dst_ip, src_ip, from_list, dst_mac, src_mac):
        from_list.append(self.name)
        node = self.port_to # get node connected to this host
        return node.handle_packet(dst_ip, src_ip,from_list, dst_mac, src_mac) # send packet to the connected node

class switch:
    def __init__(self, name, port_n):
        self.name = name
        self.mac_table = dict() # maps MAC addresses to port numbers
        self.port_n = port_n # number of ports on this switch
        self.port_to = list() 
    def add(self, node): # link with other hosts or switches
        self.port_to.append(node)
    def show_table(self):
        # display MAC table entries for this switch
        print('---------------',self.name,':')
        for entry in self.mac_table:
            print(entry,':',self.mac_table[entry])
    def clear(self):
        # clear MAC table entries for this switch
        self.mac_table.clear()
    def update_mac(self, idx, mac):
        # update MAC table with a new entry
        self.mac_table[mac] = idx
    def send(self, idx, dst_ip,src_ip, from_list, dst_mac, src_mac): # send to the specified port
        from_list.append(self.name)
        node = self.port_to[idx] 
        return node.handle_packet(dst_ip,src_ip,from_list, dst_mac, src_mac) 
    def handle_packet(self, dst_ip,src_ip, from_list, dst_mac, src_mac): # handle incoming packets
        if(from_list[-1] in host_dict):
            from_node = host_dict[from_list[-1]]
        elif(from_list[-1] in switch_dict):
            from_node = switch_dict[from_list[-1]]
        if(dst_mac in self.mac_table.keys()):
            return self.send(self.mac_table[dst_mac],dst_ip, src_ip, from_list, dst_mac, src_mac)
        for idx in range(0,self.port_n):
            if(self.port_to[idx].name in from_list):
                continue
            dst_mac = self.send(idx,dst_ip,src_ip, from_list, dst_mac, src_mac)
            if(dst_mac): #if find host update_mac
                self.update_mac(idx,dst_mac)
                self.update_mac(self.port_to.index(from_node),src_mac)
                return dst_mac
        return 0
    def show_port_to(self):
        print(self.port_to)

def add_link(tmp1, tmp2): # create a link between two nodst
    global host_dict, switch_dict
    if(tmp1 in host_dict):
        if(tmp2 in host_dict):
            host_dict[tmp1].add(host_dict[tmp2])
        else:
            host_dict[tmp1].add(switch_dict[tmp2])
    else:
        if(tmp2 in host_dict):
            switch_dict[tmp1].add(host_dict[tmp2])
        else:
            switch_dict[tmp1].add(switch_dict[tmp2])
        switch_dict[tmp1].port_n += 1
    if(tmp2 in host_dict):
        if(tmp1 in host_dict):
            host_dict[tmp2].add(host_dict[tmp1])
        else:
            host_dict[tmp2].add(switch_dict[tmp1])
    else:
        if(tmp1 in host_dict):
            switch_dict[tmp2].add(host_dict[tmp1])
        else:
            switch_dict[tmp2].add(switch_dict[tmp1])
        switch_dict[tmp2].port_n += 1
    

def set_topology():
    global host_dict, switch_dict
    hostlist = get_hosts().split(' ')
    switchlist = get_switches().split(' ')
    link_command = get_links()
    ip_dic = get_ip()
    mac_dic = get_mac()
    links = link_command.split(' ')

    host_dict = dict() # maps host names to host objects
    switch_dict = dict() # maps switch names to switch objects
    # ... create nodst and links
    for host_ in hostlist:
        host_dict[host_] = host(host_,ip_dic[host_],mac_dic[host_])
    
    for switch_ in switchlist:
        switch_dict[switch_] = switch(switch_,0)

    for link in links:
        tmp1,tmp2 = link.split(',')
        add_link(tmp1,tmp2)
        

    

def ping(tmp1, tmp2): # initiate a ping between two hosts
    global host_dict, switch_dict
    if tmp1 in host_dict and tmp2 in host_dict : 
        node1 = host_dict[tmp1]
        node2 = host_dict[tmp2]
        node1.ping(node2.ip)
    else : 
        print('a wrong command')


def show_table(tmp): # display the ARP or MAC table of a node
    global host_dict, switch_dict
    if(tmp == 'all_hosts'):
        print('ip:mac')
        for host_ in host_dict:
            host_dict[host_].show_table()
    elif(tmp == 'all_switches'):
        print('mac:port')
        for switch_ in switch_dict:
            switch_dict[switch_].show_table()
    else:
        if(tmp in host_dict):
            print('ip:mac')
            host_dict[tmp].show_table()
        elif(tmp in switch_dict):
            print('mac:port')
            switch_dict[tmp].show_table()
        else:
            print('a wrong command')

def clear(tmp):
    global host_dict, switch_dict
    if(tmp in host_dict):
        host_dict[tmp].clear()
    elif(tmp in switch_dict):
        switch_dict[tmp].clear()


def run_net():
    while(1):
        command_line = input(">> ")
        # ... handle user commands
        cmd_elements = command_line.split(' ')
        if(len(cmd_elements) == 3):
            if(cmd_elements[1] == 'ping'):
                ping(cmd_elements[0], cmd_elements[2])
            else:
                print('a wrong command')
        elif(len(cmd_elements) == 2):
            if(cmd_elements[0] == 'show_table'):
                show_table(cmd_elements[1])
            elif(cmd_elements[0] == 'clear'):
                clear(cmd_elements[1])
            else:
                print('a wrong command')
        else:
            print('a wrong command')

# def iptomac(ip):
#     ip_dic = get_ip()
#     mac_dic = get_mac()
#     name = list(ip_dic.keys())[list(ip_dic.values()).index(ip)]
#     return mac_dic[name]

    
def main():
    set_topology()
    run_net()


if __name__ == '__main__':
    main()
