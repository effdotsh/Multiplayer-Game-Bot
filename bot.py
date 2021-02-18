from websocket import WebSocketApp
import time
import random
import json
import _thread as thread
import math
import requests
import json

import os
import sys

dash_forsight = 10
dash_thresh = 1

fire_rate = 0.4
bullet_radius = 25
bullet_speed = 15
player_radius = 50

radius = (player_radius + bullet_radius) * dash_thresh

boom = 200
boom_thresh = 20

fire_timer: float = 0
x = 0
y = 0
px = 0
py = 0
id = ''
url = 'ws://aispawn.herokuapp.com/ws'
# url = "ws://localhost:3000/ws"

name = 'BotBoio'

z = 0


def set_boom(health):
    return 100 + (400 - 4 * health)


def random_dash(x, y, px, py):
    connecting_slope = (y - py) / (x - px)
    slope = -1 / connecting_slope

    orbit_x = x + (px - x) / 7
    orbit_y = y + (py + y) / 7

    mid_point = ((x + px) / 2)
    diff = abs(x - px)
    dash_x = mid_point + (diff / 4 + random.randint(int(diff / 6), int(diff / 2))) * random.choice((-1, 1))

    dash_y = slope * (dash_x - mid_point) + (py + y) / 2

    ws.send(f'vel{dash_x - x},{dash_y - y}')
    ws.send('dash')


def check_incoming(bullets, x, y, px, py):
    for b in bullets:
        if b['fired_by'] != id and 0 < b['x'] < 3000 and 0 < b['y'] < 3000 and b != bullets[0]:
            new_x = b['x']
            new_y = b['y']

            collide = False
            for i in range(dash_forsight):
                new_x += b['angle'][0]
                new_y += b['angle'][1]
                if math.dist((x, y), (new_x, new_y)) <= radius * dash_thresh:
                    collide = True
                    break

            if collide:
                random_dash(x, y, px, py)


def fire(x, y, px, py, vel_x, vel_y):
    dist = math.dist((x, y), (px, py))
    travel_time = dist / bullet_speed
    target_x = px + vel_x * travel_time
    target_y = py + vel_y * travel_time
    ws.send(f'fire{target_x - x}, {target_y - y}')


def filter_players(player):
    if player['spectating'] or not player['living']:
        return False
    else:
        return True


def ws_handler(ws, message):
    global fire_timer
    global x
    global y
    global px
    global py
    global id

    msg = json.loads(message)
    if msg['type'] == 'sync_player':
        this_player = msg['you_are']
        players = msg['info'][0]

        bx = players[this_player]['x']
        by = players[this_player]['y']
        id = players[this_player]['id']
        x = bx
        y = by

        filtered = filter(filter_players, players)

        other = 0
        p_counter = 0
        dist = 10000
        other_id = players[this_player]['id']
        for p in filtered:
            if p['id'] != id and math.dist((p['x'], p['y']), (x, y)) < dist:
                other_id = p['id']

        for p in players:
            if p['id'] == other_id:
                other = p_counter
            p_counter += 1

        px = players[other]['x']
        py = players[other]['y']

        if (players[other]['living'] and other != this_player):
            if time.time() - fire_timer >= fire_rate:
                fire(bx, by, px, py, players[other]['vel_x'], players[other]['vel_y'])
                fire_timer = time.time()

            boom = set_boom(players[this_player]['health'])

            if (math.dist((px, py), (bx, by)) > boom + boom_thresh):
                ws.send(f'vel{px - bx},{py - by}')
            elif (math.dist((px, py), (bx, by)) < boom - boom_thresh):
                ws.send(f'vel{bx - px},{by - py}')
            else:
                ws.send('vel0,0')

        else:
            ws.send(f'vel{2144 / 2 - bx},{1047 / 2 - by}')

            ws.send(f'fire{random.randint(-1000, 1000)}, {random.randint(-1000, 1000)}')

    if msg['type'] == 'sync_bullet':
        bullets = msg['info'][0]
        check_incoming(bullets, x, y, px, py)


def on_error(ws, error):
    print(error)
    os.execl(sys.executable, sys.executable, *sys.argv)


def on_open(ws):
    def check_leave(*args):
        while True:
            time.sleep(1)
            if (not should_join()):
                os.execl(sys.executable, sys.executable, *sys.argv)
    def run(*args):
        while True:
            time.sleep(0.1)
            ws.send('sync')




    ws.send(f'name{name}')
    thread.start_new_thread(run, ())
    thread.start_new_thread(check_leave, ())


def should_join():
    site = ''
    while True:
        try:
            site = requests.get('https://aispawn.herokuapp.com/info', timeout=1)
            break
        except:
            pass
    decoded = json.loads(site.content.decode('utf8'))

    num_players = 0
    for p in decoded:
        if not p['spectating'] and p['name'] != name:
            num_players += 1

    if num_players <= 1:
        return True
    else:
        return False


start_running = False
while not start_running:
    start_running = should_join()
    time.sleep(1)

ws = WebSocketApp(url, on_message=ws_handler, on_error=on_error)
ws.on_open = on_open
ws.run_forever()
