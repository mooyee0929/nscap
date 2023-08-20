import random

states_dict = {
    'idle' : '.',
    'send' : '<',
    'ing'  : '-',
    'end' : '>',
    'stop' :"|"
}

def rate(history):
    success_rate = 0
    idle_rate = 0
    collision_rate = 0
    collide = 1
    for t in range(len(history[0])-1,-1,-1):
        if(all(i[t] =='.' for i in history)):
            idle_rate+=1
        elif(any(i[t] =='|' for i in history)):
            collision_rate+=1
            collide = 1
        elif(any(i[t] =='>' for i in history)):
            success_rate+=1
            collide = 2
        elif(any(i[t] =='-' for i in history)):
            if(collide==1):
                collision_rate+=1
            elif(collide == 2):
                success_rate+=1
        elif(any(i[t] =='<' for i in history)):
            if(collide==1):
                collision_rate+=1
            elif(collide == 2):
                success_rate+=1


    success_rate/=len(history[0])
    idle_rate/=len(history[0])
    collision_rate/=len(history[0])
    return success_rate,idle_rate,collision_rate

    


def aloha(setting, show_history = False):
    random.seed(setting.seed)
    packet = setting.gen_packets()
    # print(packet)

    idxs = [0]*setting.host_num
    states = [False]*setting.host_num
    success = [True]*setting.host_num
    latency = [0]*setting.host_num
    gen_pack = ['']*setting.host_num
    history = ['']*setting.host_num
    for t in range(setting.total_time):
        for i in range(setting.host_num):
            if(t==packet[i][idxs[i]]):
                gen_pack[i] += 'V'
                if(idxs[i]<len(packet[i])-1):
                    idxs[i]+=1
            else:
                gen_pack[i] += ' '
    idxs = [0]*setting.host_num

    for t in range(setting.total_time):
        for i in range(setting.host_num):
            if(states[i]):
                if(latency[i] == 0):
                    for j in range(setting.host_num):
                        if(t>=packet[j][idxs[j]] and j!=i):
                            success[i]=False
                            success[j]=False
                    states[i] = False
                    if(success[i]):
                        history[i] += states_dict['end']
                        if(idxs[i]<len(packet[i])-1):
                            idxs[i]+=1
                        elif(idxs[i]==len(packet[i])-1):
                            packet[i].append(setting.total_time)
                            idxs[i]+=1
                        # print('send-end','pack',packet,'idx',idxs,'t: ',t)
                    else:
                        history[i] += states_dict['stop']
                        packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                        # print('resend','pack',packet,'idx',idxs,'t: ',t)
                        success[i] = True
                else:
                    history[i] += states_dict['ing']
                    latency[i] -=1
            elif(t>=packet[i][idxs[i]]):
                history[i] += states_dict['send']
                latency[i] = setting.packet_time-2
                states[i] = True
                for j in range(setting.host_num):
                    if(states[j] and j!=i):
                        success[i]=False
                        success[j]=False
                # print('pack',packet,'idx',idxs,'t: ',t)
            else:
                history[i] += states_dict['idle']
        
    if show_history:
        print('aloha')
        for i in range(setting.host_num):
            print(gen_pack[i])
            print(history[i],len(history[i]))
                
    success_rate,idle_rate,collision_rate = rate(history)

    return success_rate,idle_rate,collision_rate


def slotted_aloha(setting, show_history = False):
    random.seed(setting.seed)
    packet = setting.gen_packets()
    # print(packet)

    idxs = [0]*setting.host_num
    resend = [0]*setting.host_num
    states = [False]*setting.host_num
    success = [True]*setting.host_num
    gen_pack = ['']*setting.host_num
    history = ['']*setting.host_num
    for t in range(setting.total_time):
        for i in range(setting.host_num):
            if(t==packet[i][idxs[i]]):
                gen_pack[i] += 'V'
                if(idxs[i]<len(packet[i])-1):
                    idxs[i]+=1
            else:
                gen_pack[i] += ' '
    idxs = [0]*setting.host_num

    for t in range(0,setting.total_time,setting.packet_time):
        for i in range(setting.host_num):
            if(resend[i]>0):
                p = random.random()
                if(p<=setting.p_resend):
                    states[i] = True
            elif(packet[i][idxs[i]]<=t):
                states[i] = True

        if(sum(states)>1):
            for i in range(setting.host_num):
                if(states[i]):
                    success[i] = False

        for i in range(setting.host_num):
            if(states[i]):
                history[i] += states_dict['send'] 
                if(len(history[i])==setting.total_time):
                        continue
                for k in range(setting.packet_time-2):
                    history[i] += states_dict['ing']
                    if(len(history[i])==setting.total_time):
                        break
                if(len(history[i])==setting.total_time):
                    continue
                if(success[i]):
                    history[i]+=states_dict['end']
                    if(len(history[i])==setting.total_time):
                        continue
                    if(idxs[i]<len(packet[i])-1):
                        idxs[i]+=1
                    elif(idxs[i]==len(packet[i])-1):
                        packet[i].append(setting.total_time)
                        idxs[i]+=1
                    if(resend[i]>0):
                        resend[i] -= 1
                else:
                    history[i]+=states_dict['stop']
                    if(len(history[i])==setting.total_time):
                        continue
                    if(resend[i]==0):
                        resend[i] += 1
                states[i] = False
                success[i] = True
            else:
                for k in range(setting.packet_time):
                    history[i] += states_dict['idle']
                    if(len(history[i])==setting.total_time):
                        break


    if show_history:
        print('slotted aloha')
        for i in range(setting.host_num):
            print(gen_pack[i])
            print(history[i],len(history[i]))

    
    success_rate,idle_rate,collision_rate = rate(history)
    return success_rate,idle_rate,collision_rate

def csma(setting, show_history = False):
    random.seed(setting.seed)
    packet = setting.gen_packets()
    # print(packet)
    idxs = [0]*setting.host_num
    latency = [0]*setting.host_num
    states = [False]*setting.host_num
    success = [True]*setting.host_num
    gen_pack = ['']*setting.host_num
    history = ['']*setting.host_num
    for t in range(setting.total_time):
        for i in range(setting.host_num):
            if(t==packet[i][idxs[i]]):
                gen_pack[i] += 'V'
                if(idxs[i]<len(packet[i])-1):
                    idxs[i]+=1
            else:
                gen_pack[i] += ' '
    idxs = [0]*setting.host_num

    for t in range(setting.total_time):
        if(setting.link_delay>0):
            for i in range(setting.host_num):
                index = t-setting.link_delay
                if(index>=0):
                #link_delay!=0
                    if(states[i]):
                        if(latency[i] == 0):
                            if(any(h[index]=='-'or h[index]=='>' or h[index]=='|' for idx,h in enumerate(history) if idx!=i) and index>=0):
                                success[i] = False
                            states[i] = False
                            if(success[i]):
                                history[i] += states_dict['end']
                                if(idxs[i]<len(packet[i])-1):
                                    idxs[i]+=1
                                elif(idxs[i]==len(packet[i])-1):
                                    packet[i].append(setting.total_time)
                                    idxs[i]+=1
                                # print('send-end','pack',packet,'idx',idxs,'t: ',t)
                            else:
                                history[i] += states_dict['stop']
                                packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                                # print('resend','pack',packet,'idx',idxs,'t: ',t)
                                success[i] = True
                        else:
                            for j in range(setting.host_num):
                                if(index>=0):
                                    if((history[j][index]=='-'or history[j][index]=='>' or history[j][index]=='|') and j!=i):
                                        success[i] = False
                            history[i] += states_dict['ing']
                            latency[i] -= 1
                    elif(t>=packet[i][idxs[i]]):
                        if(any(h[index]=='-'or h[index]=='>' or h[index]=='|' for idx,h in enumerate(history) if idx!=i) and index>=0):
                            history[i]+= states_dict['idle']
                            packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                            continue
                        history[i]+= states_dict['send']
                        states[i] = True
                        latency[i] = setting.packet_time-2
                        # print('pack',packet,'idx',idxs,'t: ',t)
                    else:
                        history[i] += states_dict['idle']
                else:
                    if(states[i]):
                        if(latency[i] == 0):
                            states[i] = False
                            history[i] += states_dict['end']
                        else:
                            history[i] += states_dict['ing']
                            latency[i] -= 1

                    elif(t>=packet[i][idxs[i]]):
                        history[i]+= states_dict['send']
                        states[i] = True
                        latency[i] = setting.packet_time-2
                    else:
                        history[i] += states_dict['idle']
        else:
            for i in range(setting.host_num):
                index = t-1
                if(index>=0):
                    if(states[i]):
                        if(latency[i] == 0):
                            for j in range(setting.host_num):
                                if(states[j] and j!=i):
                                    success[i] = False
                                    success[j] = False
                            states[i] = False
                            if(success[i]):
                                history[i] += states_dict['end']
                                if(idxs[i]<len(packet[i])-1):
                                    idxs[i]+=1
                                elif(idxs[i]==len(packet[i])-1):
                                    packet[i].append(setting.total_time)
                                    idxs[i]+=1
                                # print('send-end','pack',packet,'idx',idxs,'t: ',t)
                            else:
                                history[i] += states_dict['stop']
                                packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                                # print('resend','pack',packet,'idx',idxs,'t: ',t)
                                success[i] = True
                        else:
                            history[i] += states_dict['ing']
                            latency[i] -= 1
                    elif(t>=packet[i][idxs[i]]):
                        if(any(h[index]=='-'or h[index]=='<' for idx,h in enumerate(history) if idx != i)):
                            history[i]+= states_dict['idle']
                            packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                            continue

                        states[i] = True
                        history[i]+= states_dict['send']
                        success[i] = True
                        latency[i] = setting.packet_time-2
                        # print('pack',packet,'idx',idxs,'t: ',t)
                    else:
                        history[i] += states_dict['idle']
                else:
                    if(states[i]):
                        if(latency[i] == 0):
                            states[i] = False
                            history[i] += states_dict['end']
                        else:
                            history[i] += states_dict['ing']
                            latency[i] -= 1

                    elif(t>=packet[i][idxs[i]]):
                        history[i]+= states_dict['send']
                        states[i] = True
                        latency[i] = setting.packet_time-2
                    else:
                        history[i] += states_dict['idle']
                

    if show_history:
        print('csma')
        for i in range(setting.host_num):
            print(gen_pack[i])
            print(history[i],len(history[i]))

    success_rate,idle_rate,collision_rate = rate(history)
    return success_rate,idle_rate,collision_rate

def csma_cd(setting, show_history = False):
    random.seed(setting.seed)
    packet = setting.gen_packets()
    # print(packet)
    idxs = [0]*setting.host_num
    latency = [0]*setting.host_num
    states = [False]*setting.host_num
    success = [True]*setting.host_num
    gen_pack = ['']*setting.host_num
    history = ['']*setting.host_num
    for t in range(setting.total_time):
        for i in range(setting.host_num):
            if(t==packet[i][idxs[i]]):
                gen_pack[i] += 'V'
                if(idxs[i]<len(packet[i])-1):
                    idxs[i]+=1
            else:
                gen_pack[i] += ' '
    idxs = [0]*setting.host_num
    for t in range(setting.total_time):
        if(setting.link_delay>0):
            for i in range(setting.host_num):
                index = t-setting.link_delay
                if(index>=0):
                #link_delay!=0
                    if(states[i]):
                        if(latency[i] == 0):
                            for j in range(setting.host_num):
                                if(states[j] and j!=i):
                                    success[i] = False
                                    success[j] = False
                            states[i] = False
                            if(success[i]):
                                history[i] += states_dict['end']
                                if(idxs[i]<len(packet[i])-1):
                                    idxs[i]+=1
                                elif(idxs[i]==len(packet[i])-1):
                                    packet[i].append(setting.total_time)
                                    idxs[i]+=1
                                # print('send-end','pack',packet,'idx',idxs,'t: ',t)
                            else:
                                history[i] += states_dict['stop']
                                packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                                # print('resend','pack',packet,'idx',idxs,'t: ',t)
                                success[i] = True
                        else:
                            if(any(h[index]=='-'or h[index]=='>'or h[index]=='|' for idx, h in enumerate(history) if idx != i)):
                                history[i]+= states_dict['stop']
                                packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                                success[i] = True
                                states[i] = False
                                continue
                            history[i] += states_dict['ing']
                            latency[i] -= 1
                    elif(t>=packet[i][idxs[i]]):
                        if(any(h[index]=='-'or h[index]=='>'or h[index]=='|' for idx, h in enumerate(history) if idx != i)):
                            history[i]+= states_dict['idle']
                            packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                            continue
                        states[i] = True
                        history[i]+= states_dict['send']
                        success[i] = True
                        latency[i] = setting.packet_time-2
                        # print('pack',packet,'idx',idxs,'t: ',t)
                    else:
                        history[i] += states_dict['idle']
                else:
                    if(states[i]):
                        if(latency[i] == 0):
                            states[i] = False
                            history[i] += states_dict['end']
                        else:
                            history[i] += states_dict['ing']
                            latency[i] -= 1

                    elif(t>=packet[i][idxs[i]]):
                        history[i]+= states_dict['send']
                        states[i] = True
                        latency[i] = setting.packet_time-2
                    else:
                        history[i] += states_dict['idle']
        else:
            for i in range(setting.host_num):
                index = t-1
                if(index>=0):
                    if(states[i]):
                        if(latency[i] == 0):
                            for j in range(setting.host_num):
                                if(states[j] and j!=i):
                                    success[i] = False
                                    success[j] = False
                            states[i] = False
                            if(success[i]):
                                history[i] += states_dict['end']
                                if(idxs[i]<len(packet[i])-1):
                                    idxs[i]+=1
                                elif(idxs[i]==len(packet[i])-1):
                                    packet[i].append(setting.total_time)
                                    idxs[i]+=1
                                # print('send-end','pack',packet,'idx',idxs,'t: ',t)
                            else:
                                history[i] += states_dict['stop']
                                packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                                # print('resend','pack',packet,'idx',idxs,'t: ',t)
                                success[i] = True
                        else:
                            for j in range(setting.host_num):
                                if(states[j] and j!=i):
                                    success[i] = False
                                    success[j] = False
                            if(success[i] == False):
                                history[i] += states_dict['stop']
                                packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                                states[i] = False
                                continue
                            history[i] += states_dict['ing']
                            latency[i] -= 1
                    elif(t>=packet[i][idxs[i]]):
                        if(any(h[index]=='-'or h[index]=='<' for h in history)):
                            history[i]+= states_dict['idle']
                            packet[i][idxs[i]] =(random.randrange(t+1,t+setting.max_colision_wait_time))
                            continue

                        states[i] = True
                        history[i]+= states_dict['send']
                        success[i] = True
                        latency[i] = setting.packet_time-2
                        # print('pack',packet,'idx',idxs,'t: ',t)
                    else:
                        history[i] += states_dict['idle']
                else:
                    if(states[i]):
                        if(latency[i] == 0):
                            states[i] = False
                            history[i] += states_dict['end']
                        else:
                            history[i] += states_dict['ing']
                            latency[i] -= 1

                    elif(t>=packet[i][idxs[i]]):
                        history[i]+= states_dict['send']
                        states[i] = True
                        latency[i] = setting.packet_time-2
                    else:
                        history[i] += states_dict['idle']


    if show_history:
        print('csma/cd')
        for i in range(setting.host_num):
            print(gen_pack[i])
            print(history[i],len(history[i]))

    success_rate,idle_rate,collision_rate = rate(history)
    return success_rate,idle_rate,collision_rate
