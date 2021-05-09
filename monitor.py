#!/usr/bin/env
import os
import time
import asyncio
import websockets
import hmac
import json
import hashlib
import requests

async def listen_forever(uri, delay_alert_threshold):
    print("connecting")
    async with websockets.connect(uri) as ws:
        print("connection established")

        #continously read messages from the websocket and process for delay
        while True:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                on_message(message, delay_alert_threshold)
            except (asyncio.TimeoutError) as err:
                print("no message for 10 seconds, waiting...")
            except (websockets.exceptions.ConnectionClosed) as err:
                print(f"conn closed, {err}")               

def on_message(message, delay_alert_threshold):
    try:
        data = json.loads(message)
        if data.get("e") == "executionReport":
            tx_time = data['T']
            order_id = data['c']
            event_time = data['E']
            delay = int(event_time - tx_time)

            #check if the difference between the Event time and the TX time exceeds the delay thresshold
            if delay > delay_alert_threshold:
                print(f"ALERT: exec event for order {order_id} is delayed")
    except:
        print("error processing message")

def request(api_key, secret, method, uri, signed = False, **params):
    session = requests.session()
    session.headers.update({
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-MBX-APIKEY': api_key
    })

    request_uri = ""

    if signed:
        params["timestamp"] = int(time.time() * 1000 + 1000)
        query = '&'.join(f"{key}={params[key]}" for key in params)
        signature = hmac.new(secret.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
        request_uri = f"{uri}?{query}&signature={signature}"
    else:
        if params:
            query = '&'.join(f"{key}={params[key]}" for key in params)
            request_uri = f"{uri}?{query}"
        else:
            request_uri = uri

    return getattr(session, method)(request_uri).json()

if __name__ == '__main__':

    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("PUBLIC")
    secret = os.getenv("SECRET")
    delay_alert_threshold = int(os.getenv("DELAY"))
    mock = os.getenv("MOCK")

    ws_url = "wss://testnet.binance.vision/ws"
    api_url = "https://testnet.binance.vision/api/v3"
    listenkey_endpoint = "/userDataStream"
    order_endpoint = "/order"

    #obtain listen key
    listen_key = request(api_key, secret, 'post', f"{api_url}{listenkey_endpoint}").get('listenKey', None)
    
    if listen_key != None:
        uri = f"{ws_url}/ws/{listen_key}"
        loop = asyncio.get_event_loop()
        
        #places a new order every 2 seconds
        async def periodic_order():
            while True:
                new_order = request(api_key, secret, 'post', f"{api_url}{order_endpoint}", True, symbol="ETHUSDT", side="BUY", type="MARKET",quantity="0.1",recvWindow="5000")
                await asyncio.sleep(2)

        #if mock is set to YES, schedule a new order to be placed periodically for 30 seconds
        if mock == "yes":
            task_orders = loop.create_task(periodic_order())
            loop.call_later(30, lambda: task_orders.cancel())

        #ping the listen key every 30 minutes to keep it alive
        async def keep_alive():
            while True:
                await asyncio.sleep(1800)
                request(api_key, secret, 'put', f"{api_url}{listenkey_endpoint}", False, listenKey=listen_key)

        task_keepalive = loop.create_task(keep_alive())

        #schedule websocket task that will listen for execution reports
        loop.run_until_complete(listen_forever(uri, delay_alert_threshold = delay_alert_threshold))
        task_keepalive.cancel()
        print("done")
    

