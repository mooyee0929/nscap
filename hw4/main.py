import copy

link_cost = [
    [  0,   2,   5,   1, 999, 999],
    [  2,   0,   3,   2, 999, 999],
    [  5,   3,   0,   3,   1,   5],
    [  1,   2,   3,   0,   1, 999],
    [999, 999,   1,   1,   0,   2],
    [999, 999,   5, 999,   2,   0]
    ]
testdata =  [
    [0, 4, 1, 999], 
    [4, 0, 2, 999], 
    [1, 2, 0, 3], 
    [999, 999, 3, 0]
]

class Node:
    def __init__(self, id, link):
        self.table = dict()
        for i in range(len(link)):
            self.table[i] = 999
        self.table[id] = 0
        self.linkstate = [id]
        self.rip_check = True
        self.buffer = []
        self.id = id
        self.link = dict()
        for i,v in enumerate(link):
            if v == 0 or v == 999:
                continue
            self.link[i] = v
            self.table[i] = v


def end_rip(nodelist):
    for i in range(len(nodelist)):
        if nodelist[i].rip_check == True:
            return True
    return False

def end_ospf(graph_dis):
    for i in range(len(graph_dis)):
        if len(graph_dis[i].linkstate) != len(graph_dis):
            return True
    return False

def print_cost(node_list):
        for i in range(len(node_list)):
            for j in range(len(node_list[i].table)):
                print(node_list[i].table[j],end=' ')
            print(end='\n')


def return_cost(node_list):
    result = []
    for i in range(len(node_list)):
        tmp = []
        for j in range(len(node_list[i].table)):
            tmp.append(node_list[i].table[j])
        result.append(tmp)

    return result

                


def run_ospf(link_cost: list) -> tuple():
    graph_cost = []
    send_list = []

    node_list = []
    for i in range(len(link_cost)):
        node_list.append(Node(i,link_cost[i]))

    
    node_list_copy = copy.deepcopy(node_list)
    

    while(end_ospf(node_list)):
        for src,s_node in enumerate(node_list_copy):
            for ori in s_node.linkstate:
                for dst in node_list_copy[src].link:
                    if ori not in node_list[dst].linkstate:
                        node_list[dst].linkstate.append(ori)
                        send_list.append((src,ori,dst))
                        # print(src,ori,dst)


        for idx,node in enumerate(node_list):
            for s in list(set(node.linkstate).difference(set(node_list_copy[idx].linkstate))):
                for d in node_list[idx].table:
                    node.table[d] = min(node.table[d],node_list[idx].table[s]+node_list[s].table[d])
                    node_list[d].table[idx] = min(node.table[d],node_list[idx].table[s]+node_list[s].table[d])
                        


        node_list_copy = copy.deepcopy(node_list)
        
    graph_cost = return_cost(node_list)
    return (graph_cost,send_list)
    print_cost(node_list)
    




def run_rip(link_cost: list) -> tuple():
    graph_cost = []
    send_list = []


    node_list = []
    for i in range(len(link_cost)):
        node_list.append(Node(i,link_cost[i]))

    node_list_copy = copy.deepcopy(node_list)

    while(end_rip(node_list_copy)):
        for src,node in enumerate(node_list_copy):
            if node.rip_check == True:
                for dst in node_list_copy[src].link:
                    node_list[dst].buffer.append(src)
                    send_list.append((src,dst))
                    # print(src,dst)

        for idx,node in enumerate(node_list):
            if node.rip_check == True:
                for s in node.buffer:
                    for d in node_list_copy[idx].table:
                        node.table[d] = min(node.table[d],node_list_copy[idx].table[s]+node_list_copy[s].table[d])

        
        for idx,node in enumerate(node_list):
            node.buffer.clear()
            if node_list[idx].table == node_list_copy[idx].table:
                node_list[idx].rip_check = False            
        
        node_list_copy = copy.deepcopy(node_list)

    graph_cost = return_cost(node_list)
    return (graph_cost,send_list)
    print_cost(node_list)
        



def main():
    print(run_ospf(link_cost))
    print(run_ospf(testdata))
    print(run_rip(link_cost))
    print(run_rip(testdata))




if __name__=='__main__':
    main()