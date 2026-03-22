import sys
import json
import time
import requests
import websocket

BASE_URL = "https://live.rankedin.com"
HUB_PATH = "/scores"
SEP = "\x1e"


def negotiate():
    r = requests.post(
        BASE_URL + HUB_PATH + "/negotiate?negotiateVersion=1",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/"
        }
    )
    r.raise_for_status()
    return r.json()


def on_message(ws, message):
    for frame in message.split(SEP):
        if not frame.strip():
            continue

        data = json.loads(frame)
        t = data.get("type")

        if t == 1:  # server event
            print(f"\nEVENT: {data.get('target')}")
            print(json.dumps(data.get("arguments"), indent=2, ensure_ascii=False))


def on_open(ws, court_id):
    # handshake
    ws.send(json.dumps({"protocol": "json", "version": 1}) + SEP)

    # join court
    join = {
        "type": 1,
        "target": "JoinCourtRoom",
        "arguments": [{
            "courtId": court_id,
            "UserId": "0",
            "StreamId": 0
        }],
        "invocationId": "0"
    }
    ws.send(json.dumps(join) + SEP)
    print(f"Connected to court {court_id}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python rankedin_ws.py <court_id>")
        return

    court_id = int(sys.argv[1])

    while True:
        try:
            print("Negotiating...")
            nego = negotiate()

            ws_url = nego["url"].replace("https://", "wss://")
            ws_url += "&access_token=" + nego["accessToken"]

            ws = websocket.WebSocketApp(
                ws_url,
                header={"Origin": BASE_URL},
                on_open=lambda ws: on_open(ws, court_id),
                on_message=on_message
            )

            ws.run_forever(ping_interval=None)

        except Exception as e:
            print("Error:", e)

        print("Reconnect in 5s...")
        time.sleep(5)


if __name__ == "__main__":
    main()
