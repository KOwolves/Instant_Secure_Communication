import socket, select
import json


def chatserver(flag, client, gnum, name,groupmsg,socketmsg,contactingnames,GROUP):
    contactingnames[gnum] = []
    for i in range(len(contactingnames[gnum])):
        if name != contactingnames[gnum][i]:
            contactingnames[gnum].append(name)
    print(contactingnames)
    def enterGroup(client, gnum, name,groupmsg,socketmsg,contactingnames):

        if gnum>GROUP:
            client.send('invalid gnum'.encode())
        else:
            usermsg = client.getpeername()
            groupmsg[gnum].append(usermsg)
            socketmsg[gnum].append(client)
            contactingnames[gnum].append(name)
            wel = 'welcome into the chatting room'
            print(wel)
            for username in contactingnames[gnum]:
                if username is not name:
                    wel = wel + ' '+username
            wel = wel + ' is also in the group'
            wel = wel.encode()
            client.send(wel)

            print(name+' enters the group '+str(gnum))
            chat(gnum, id)



    def create_group(client,gnum,name,groupmsg,socketmsg,contactingnames):
        print('function-c')
        contactingnames[gnum].append(name)
        usermeg = client.getpeername()
        print(gnum)
        #print(type(groupId))
        groupmsg[gnum].append(usermeg)
        socketmsg[gnum].append(client)
        wel = 'successfully create a chatting-group,your group number is:'\
              +str(gnum)
        state = 66

        try:
            client.send(wel.encode())
        except:
            print('send wel error')


        print(name + ' create the group ' + str(gnum))
        #chat(gnum, id,groups,groupId)




    def chat(gnum, name , info, conn,socketmsg):
        #r, w, e = select.select(groups[gnum], [], [])
        temp = conn
        for user in socketmsg[gnum]:
            try:
                data = name +':'+info
                if user is not temp:
                    user.send(data)
            except:
                data = name+' leave the room'
                data = data.encode()
                if user is not temp:
                    try:
                        user.send(data)
                    except:
                        print('send error')
                #groups[gnum].remove(temp)
                #groupId[gnum].remove(id)
                #for client in w:
                #    if client is not temp:
                #       try:
                #            client.send(data)
                #        except:
                #            print('send error')

    print('function1')


    if flag == 1:
        print('functionf1')
        create_group(client, gnum, name,groupmsg,socketmsg,contactingnames)
    elif flag == 2:
        enterGroup(client, gnum, name,groupmsg,socketmsg,contactingnames)
    else:
        client.sent('invalid command'.encode())