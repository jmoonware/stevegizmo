import live_settings as settings
from project import StartDataLogging
from project import simulate_receive_from_rb
message = input("Type a message (as if coming from Rockblock device: ")
simulate_receive_from_rb(message)
