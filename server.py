import socket
import threading
import time
from datetime import datetime
from uuid import uuid4
from constants import *

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
chatroom_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

'''
CONNECTIONS: used for filtering out inactive clients
{
    udp_address: {
        rooms: []
        last_active_time: datetime
    }
}
'''
connections = {}

'''
ROOMS
{
    room_name: {
        udp_address: {
            role: 
            user_name:
            token:
        },
    },
}
'''
rooms = {}

def register_client(length, addr):
    try:

        sock.sendto(int.to_bytes(len(connections)), addr)

        user_name_bytes, client = sock.recvfrom(length)
        user_name = user_name_bytes.decode()
            
        connection = {
            "user_name": user_name,
            "last_send_timestamp": datetime.timestamp(datetime.now())
        }

        connections[addr] = connection
        print(connections)
    
    except:
        print('An exception occurred')

def authenticate(room_name, addr, token):

    if room_name in rooms:
        room = rooms[room_name]
        if addr in room:
            return room[addr]["token"] == token
    
    return False

def update_connection(room_name, addr):
    if addr in connections:
        connections[addr]["rooms"].append(room_name)
    else:
        user = {
            "rooms": [room_name],
            "last_active_time": datetime.timestamp(datetime.now())
        }
        connections[addr] = user

def forward_message():
    try:
        while True:
            req, client_address = sock.recvfrom(4096)
            print('message received')

            room_name_len = int.from_bytes(req[:1], 'big')
            token_len = int.from_bytes(req[1:2], 'big')

            room_name = req[2:2 + room_name_len].decode()
            token = req[2 + room_name_len : 2 + room_name_len + token_len].decode()
            message = req[2 + room_name_len + token_len:].decode()

            if authenticate(room_name, client_address, token):
                client = rooms[room_name][client_address]
                user_name = client["user_name"]
                forwarded_message = '{}: {}'.format(user_name, message)
                print(forwarded_message)

                for addr in rooms[room_name]:
                    if addr != client_address:
                        sock.sendto(forwarded_message.encode(), addr)
            
                connections[client_address]["last_active_time"] = datetime.timestamp(datetime.now())
    
    except:
        print('An excpetion occurred')

def invalidate_client(addr):
    client_rooms = connections[addr]["rooms"]

    for room in client_rooms:
        if (room in rooms) and (addr in rooms[room]):
            del rooms[room][addr]
    
    del connections[addr]

def remove_inactive_clients():
    while True:
        time.sleep(10)
        current_timestamp = datetime.timestamp(datetime.now())
        delete_keys = [key for key in connections if current_timestamp - connections[key]["last_active_time"] > 60]

        if len(delete_keys) > 0:
            print("detect inactive clients")
            for key in delete_keys:
                invalidate_client(key)

def create_room(room_name, user_name, host, port, token):

    addr = (host, port)

    room = {
        addr : {
            "role": "host",
            "user_name": user_name,
            "token": token,
            "last_active_time": datetime.timestamp(datetime.now())
        }
    }

    rooms[room_name] = room

    update_connection(room_name, addr)
    return

def join_room(room_name, user_name, host, port, token):

    if not room_name in rooms:
        raise NoRoomError

    user = {
        "role": "guest",
        "user_name": user_name,
        "token": token
    }

    addr = (host, port)

    rooms[room_name][addr] = user

    message = f'{user_name} joined the room!!'
    for addr in rooms[room_name]:
        sock.sendto(message.encode(), addr)

    update_connection(room_name, addr)
    return
    

def handle_initial_request():
    try:
        while True:
            print("waiting for connections...")
            # wait for client connection
            conn, client = chatroom_sock.accept()
            print(f'received connection from {client}')
            ''' HEADER
                room name length : 1 byte
                operation        : 1 byte (create, join)
                state            : 1 byte (initializatin, initial response, complete response)
                host length      : 1 byte
                user name length : 1 bytes
                port             : 27 bytes
            '''
            header = conn.recv(32)

            # decode information contained in the header
            room_name_len = int.from_bytes(header[:1], "big")
            operation = int.from_bytes(header[1:2], "big")
            host_len = int.from_bytes(header[3:4], "big")
            user_name_len = int.from_bytes(header[4:5], "big")
            port = int.from_bytes(header[5:], "big")

            # receive body
            body = conn.recv(room_name_len + host_len + user_name_len)
            # decode body to retrieve room name & user name
            room_name = body[:room_name_len].decode()
            host = body[room_name_len:room_name_len + host_len].decode()
            user_name = body[room_name_len + host_len:].decode()

            # immediate response with updated state (SERVER_INITIALIZATION -> INITIAL_RESPONSE)
            initial_response = header[:2] + INITIAL_RESPONSE.to_bytes(1, 'big') + INITIAL_RESPONSE.to_bytes(29, 'big')
            conn.sendall(initial_response)

            '''
            Register client
                - if operation is CREATE, give the user host access token
                - if operation is JOIN, give guest access token
            '''
            token = str(uuid4())
            if operation == CREATE_ROOM:
                create_room(room_name, user_name, host, port, token)
            else:
                try:
                    join_room(room_name, user_name, host, port, token)
                except NoRoomError:
                    err = room_name_len.to_bytes(1, 'big') + operation.to_bytes(1, 'big') + NO_ROOM_ERROR.to_bytes(1, 'big')
                    conn.sendall(err)
                    print("user sent an invalid room name.")
                    conn.close()
                    continue
            
            # send complete message
            header = room_name_len.to_bytes(1, 'big') + operation.to_bytes(1, 'big') + COMPLETE_RESPONSE.to_bytes(1, 'big') + len(token).to_bytes(29, 'big')
            conn.sendall(header)
            conn.sendall(token.encode())
            conn.close()

    except:
        print('an exception occurred')
    
    finally:
        print('closing TCP socket...')
        chatroom_sock.close()

def main():
    sock.bind((SERVER_ADDRESS_FROM_CLIENT, SERVER_PORT))
    chatroom_sock.bind((SERVER_ADDRESS_FROM_CLIENT, CHATROOM_SERVER_PORT))
    chatroom_sock.listen(10)

    regist_thread = threading.Thread(target=handle_initial_request)
    forward_thread = threading.Thread(target=forward_message)
    remove_thread = threading.Thread(target=remove_inactive_clients)
    
    regist_thread.start()
    forward_thread.start()
    remove_thread.start()

    regist_thread.join()
    forward_thread.join()
    remove_thread.join()

if __name__ == "__main__":
    main()