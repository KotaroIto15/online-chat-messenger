# server addresses
SERVER_ADDRESS_FROM_CLIENT = '0.0.0.0'
SERVER_PORT = 9001
CHATROOM_SERVER_PORT = 9002
SERVER_ADDRESS_FROM_CLIENT = '127.0.0.1'
CLIENT_ADDRESS = '0.0.0.0'

# request type
CREATE_ROOM = 1
JOIN_ROOM = 2
EXIT = 3

# state
SERVER_INITIALIZATION = 0
INITIAL_RESPONSE = 1
COMPLETE_RESPONSE = 2
NO_ROOM_ERROR = 3

AUTHENTICATED = 200
UNAUTHENTICATED = 401

FIRST_PROMPT = '''
Please select the option below.
1. Create a chat room
2. Join the chat room
3. Exit
'''

class NoRoomError(Exception):
    pass