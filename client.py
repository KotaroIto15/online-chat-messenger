import socket
import threading

from constants import *

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

connection_established = threading.Event()
stop_program = threading.Event()

user_name = ""
room_name = ""
token = ""

def send_message():
    print('send_message: STARTED')
    try:
        while True:

            if stop_program.is_set():
                break

            if not connection_established.is_set():
                continue

            message = input("")
            print("\033[1A\033[1A")
            print(f'{user_name}: {message}')

            if message == 'exit':
                connection_established.clear()
                continue

            header = len(room_name).to_bytes(1, 'big') + len(token).to_bytes(1, 'big')
            body = f'{room_name}{token}{message}'
            body_bytes = bytes(body, encoding='utf-8')
            sock.sendto(header + body_bytes, (SERVER_ADDRESS_FROM_CLIENT, SERVER_PORT))
    except:
        print('An exception occurred')
    finally:
        print('send_message: STOPPED')

def receive_message():
    print('receive_message: STARTED')
    try:
        while True:

            if stop_program.is_set():
                break
            
            if not connection_established.is_set():
                continue

            data, server = sock.recvfrom(4096)
            message = data.decode()
            print(message)
    
    except:
        print("See you again!!")
    
    finally:
        print("receive_message: STOPPED")

def main():

    global user_name, room_name, token


    sock.bind((CLIENT_ADDRESS, 0))
    sock_port = sock.getsockname()[1]

    user_name = input("please enter your user name: ")

    send_thread = threading.Thread(target = send_message)
    receive_thread = threading.Thread(target = receive_message)

    send_thread.start()
    receive_thread.start()

    while True:

        if stop_program.is_set():
            break

        if connection_established.is_set():
            continue

        print('setting up connection...')
        # socket initialization
        chatroom_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        operation = int(input(FIRST_PROMPT))

        if operation == EXIT:
            stop_program.set()
            break

        chatroom_sock.connect((SERVER_ADDRESS_FROM_CLIENT, CHATROOM_SERVER_PORT))
    
        room_name = input("What's your room name? ") if operation == CREATE_ROOM else input("What's the room name? ")
        header = len(room_name).to_bytes(1, "big") + operation.to_bytes(1, "big") + SERVER_INITIALIZATION.to_bytes(1, "big") + len(SERVER_ADDRESS_FROM_CLIENT).to_bytes(1, "big") + len(user_name).to_bytes(1, 'big') + sock_port.to_bytes(27, "big")
        chatroom_sock.sendall(header)

        body = bytes(f"{room_name}{SERVER_ADDRESS_FROM_CLIENT}{user_name}", encoding="utf-8")
        chatroom_sock.sendall(body)
       
        header = chatroom_sock.recv(32)
        state = int.from_bytes(header[2:3], "big")

        if state == INITIAL_RESPONSE:
            header = chatroom_sock.recv(32)
            state = int.from_bytes(header[2:3], "big")
            if state == COMPLETE_RESPONSE:
                token_size = int.from_bytes(header[3:], "big")
                token = chatroom_sock.recv(token_size).decode()
                connection_established.set()
            elif state == NO_ROOM_ERROR:
                print(f'room name {room_name} does not exist. Please try with a different room name.')
                continue
            else:
                print('an exception occurred')
                break

        else:
            print('an error occurred')
            break

    chatroom_sock.close()
    sock.close()


if __name__ == "__main__":
    main()