# Python Implementation of the Spades Server

To run a test on the Game object: 

`python spadesgame.py`

To run the Server on port 9000:

`python spadesserver.py 9000`


## Notes:

To run at my house: `python spadesserver.py -i 192.168.1.10 9000`

To run on the ec2: `python spadesserver.py -i 0.0.0.0 9005`


## TODO:
 - Add logging
 - Add threading to game updates
 - Fix dumb players
 - Test!