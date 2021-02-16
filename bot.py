from websocket import WebSocketApp
import time
import random
import json
import _thread as thread
import math

dash_forsight = 5
dash_accelerator = 1
dash_thresh = 3

fire_rate = 0.4
bullet_radius = 25
bullet_speed =15
player_radius = 50

boom = 400
boom_thresh = 30

fire_timer: float = 0
x = 0
y = 0
px = 0
py = 0
id = ''
url = 'wss://aispawn.herokuapp.com/ws'
# url = "ws://localhost:3000/ws"


def random_dash(x, y, px, py):
  connecting_slope = (y-py)/(x-px)
  slope = -1/connecting_slope

  orbit_x = x + (px-x)/7
  orbit_y = y + (py+y)/7

  mid_point = ((x+px)/2)
  diff = abs(x-px)
  dash_x = mid_point + (diff/3 + random.randint(int(diff/6), int(diff/2)))*random.choice((-1, 1))

  dash_y = slope*(dash_x - mid_point) + (py+y)/2

  ws.send(f'vel{dash_x-x},{dash_y-y}')
  ws.send('dash')

def check_incoming(bullets, x, y, px, py):
  for b in bullets:
    # print(b['id'])
    if b['fired_by']!=id:
      new_x = b['x'] + b['angle'][0] * dash_accelerator
      new_y = b['y'] + b['angle'][1] * dash_accelerator

      if (math.dist((new_x, new_y), (x, y)) <= (bullet_radius+player_radius)*dash_thresh or  math.dist((b['x'], b['y']), (x, y)) <= (bullet_radius+player_radius)*dash_thresh):
        random_dash(x, y, px, py)
def fire(x, y, px, py, vel_x, vel_y):
  dist = math.dist((x, y), (px, py))
  travel_time = dist/bullet_speed
  target_x = px + vel_x*travel_time
  target_y = py + vel_y*travel_time
  ws.send(f'fire{target_x-x}, {target_y-y}')


def ws_handler(ws, message):
  global fire_timer
  global x
  global y
  global px
  global py
  global id
  msg=json.loads(message)
  if msg['type']=='sync_player':
      this_player = msg['you_are']
      other = 1-this_player
      players = msg['info'][0]
      px = players[other]['x']
      py = players[other]['y']

      bx=players[this_player]['x']
      by=players[this_player]['y']
      id = players[this_player]['id']
      x = bx
      y = by
      # print(players[other])
      if(players[other]['living']):
        if time.time() - fire_timer >= fire_rate:
          fire(bx, by, px, py, players[other]['vel_x'], players[other]['vel_y'])
          fire_timer=time.time()

        if(math.dist((px, py),(bx, by)) > boom+boom_thresh):
          ws.send(f'vel{px-bx},{py-by}')
        elif(math.dist((px, py),(bx, by)) < boom-boom_thresh):
          ws.send(f'vel{bx-px},{by-py}')
        else:
          ws.send('vel0,0')

      else:
        ws.send(f'fire{random.randint(-1000, 1000)}, {random.randint(-1000, 1000)}')
      
  if msg['type']=='sync_bullet':
    bullets = msg['info'][0]
    check_incoming(bullets, x, y, px, py)

def on_error(ws, error):
    print(error)

def on_open(ws):
    def run(*args):
      while True:
        time.sleep(0.1)
        ws.send('sync')
    ws.send('nameBotBoio')
    thread.start_new_thread(run, ())

ws = WebSocketApp(url, on_message=ws_handler, on_error = on_error)
ws.on_open = on_open
ws.run_forever()

