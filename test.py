import json
json_string = '{"first_name": "Guido", "last_name":"Rossum"}'
parsed_json = json.loads(json_string)


d = {
    'first_name': 'Guido',
    'second_name': 'Rossum',
    'titles': ['BDFL', 'Developer'],
}

print(json.dumps(d))


server_status = {'type' : 'status',
                 'players' : ['EJ', 'Michael', 'David', 'Paige'], 
                 'team1' : ['EJ', 'Michael'],
                 'team2' : ['David','Paige'],
                 'score1' : 0,
                 'score2' : 0}
print json.dumps(server_status)


server_hand = {'type'   : 'hand',
               'cards'  : ['S5', 'S6', 'HQ', 'DA', 'C3', 'CK'],
               'bids'   : [['Michael', 5, 3], ['EJ', 0, 0],['David', 4, 1], ['Paige', 4, 0]],
               'trick'  : [['Michael', 'S2'], ['Paige', 'HA']],
               'turn'   : 'Michael',
               'action' : 'card'}
print json.dumps(server_hand)

server_error = {'type' : 'error',
                'error' : 'card not available'}
print json.dumps(server_error)



client_request = {'type' : 'request',
                  'request' : 'status'}
print json.dumps(client_request)

client_init = {'type' : 'init', 
               'id'   : 'David',
               'team' : 1}
print json.dumps(client_init)

client_bid = {'type' : 'bid', 
               'bid'   : 5}
print json.dumps(client_bid)

client_card = {'type' : 'card', 
               'card' : 'S5'}
print json.dumps(client_card)