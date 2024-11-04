from flask import Flask, render_template, jsonify, request
import asyncio
import requests
import logging
import aiohttp,time
import asyncio
import string
import random



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

user_sessions = {}
def transaction_id():
    return "".join(random.choice(string.ascii_letters) for x in range(12))

JANUS_HTTP_URL = "http://localhost:8088/janus"  # HTTP endpoint for Janus

async def wait_for_janus_jsep(session_url, transaction_id):
    async with aiohttp.ClientSession() as session:
        while True:
            params = {"maxev": 1, "rid": int(time.time() * 1000)}
            # Make the request to the correct endpoint
            async with session.get(f"{session_url}", params=params) as response:
                # Check if the response is successful
                if response.status != 200:
                    continue

                data = await response.json()
                print(data)
                # Check for the expected event and matching transaction
                if data.get("janus") == "event" and data.get("transaction") == transaction_id:
                    jsep = data.get("jsep")
                    if jsep:
                        return jsep  # Return the full event containing `jsep`

            # Optional: delay between polls
            await asyncio.sleep(1)

async def wait_for_janus(session_url, transaction_id):
    async with aiohttp.ClientSession() as session:
        while True:
            params = {"maxev": 1, "rid": int(time.time() * 1000)}
            # Make the request to the correct endpoint
            async with session.get(f"{session_url}", params=params) as response:
                # Check if the response is successful
                if response.status != 200:
                    continue

                data = await response.json()
                # Check for the expected event and matching transaction
                if data.get("janus") == "event" and data.get("transaction") == transaction_id:
                    return data
            # Optional: delay between polls
            await asyncio.sleep(1)  
                         
async def janus_request(message, session_url=JANUS_HTTP_URL):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(session_url, json=message) as response:
                response_json = await response.json()
                if response.status == 200:
                    logger.info("Received response: %s", response_json)
                    return response_json
                else:
                    logger.error("Error during HTTP communication: %s", response.status)
                    raise Exception("Janus HTTP request failed with status %s" % response.status)
    except Exception as e:
        logger.error("Error during HTTP communication: %s", e)
        raise

@app.route('/add_track/<room_id>', methods=['POST'])
async def add_track(room_id):
    try:
        data=request.get_json()
        user_id = request.args.get('user_id')
        if user_id not in user_sessions:
            return jsonify({"error": "User session not found"}), 400
        
        session_id = user_sessions[user_id]["session_id"]
        handle_id = user_sessions[user_id]["handle_id"]

        # Join the room as a publisher
        join_request = {
            "janus": "message",
            "body": {
                "request": "join",
                "ptype": "publisher",
                "room": int(room_id)
            },
            "transaction": transaction_id(),
            "session_id": session_id,
            "handle_id": handle_id
        }
        await janus_request(join_request)
        trans_id= transaction_id()

        # Send offer to Janus to start peer connection
        publish_request = {
            "janus": "message",
            "body": {"request": "publish", "room": room_id,"video":True,"audio":False},
            "jsep": {"type": "offer", "sdp":data['sdp']},
            "transaction":trans_id,
            "session_id": session_id,
            "handle_id": handle_id
        }
        publish_response = await janus_request(publish_request)
        if publish_response.get("janus") == "ack":
            # Wait for the success response with jsep
            publish_response = await wait_for_janus_jsep(JANUS_HTTP_URL+f'/{session_id}', trans_id)
            
        return jsonify({"sdp": publish_response["sdp"]})
    except Exception as e:
        logger.error("Error adding track to room: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/subscribe/<room_id>', methods=['POST'])
async def subscribe(room_id):
    try:
        user_id = request.args.get('user_id')
        if user_id not in user_sessions:
            return jsonify({"error": "User session not found"}), 400

        session_id = user_sessions[user_id]["session_id"]
        handle_id = user_sessions[user_id]["handle_id"]

        # Step 1: List available participants (publishers) to get feed ID
        list_participants_request = {
            "janus": "message",
            "body": {"request": "listparticipants", "room": int(room_id)},
            "transaction": transaction_id(),
            "session_id": session_id,
            "handle_id": handle_id
        }
        
        list_response = await janus_request(list_participants_request)
        participants = list_response["plugindata"]["data"].get("participants", [])
        if not participants:
            return jsonify({"error": "No available feeds in this room"}), 404

        # Assume we are subscribing to the first participant's feed
        feed_id = participants[0]["id"]
        tnas_id= transaction_id()
        # Step 2: Send subscribe request with the feed ID
        join_request = {
            "janus": "message",
            "body": {
                "request": "join",
                "ptype": "subscriber",  # Listener role for subscribing
                "room": int(room_id),
                # "feed":feed_id
                "streams": [{
                    "feed":feed_id
                }]
            },
            "transaction":tnas_id,
            "session_id": session_id,
            "handle_id": handle_id
        }
        join_response = await janus_request(join_request)
        # Return the SDP offer from Janus for the client to set as remote description
        if join_response.get("janus") == "ack":
            # Wait for the success response with jsep
            jsep_offer = await wait_for_janus_jsep(JANUS_HTTP_URL+f'/{session_id}', tnas_id)

        return jsonify(jsep_offer)
    except Exception as e:
        logger.error("Error subscribing to room: %s", e)
        return jsonify({"error": str(e)}), 500
    
    
@app.route('/complete_connection', methods=['POST'])
async def complete_connection():
    data = request.get_json()
    user_id = data.get("user_id")
    room_id = data.get("room_id")
    sdp = data.get("sdp")
    type = data.get("type")
    if user_id not in user_sessions:
        return jsonify({"error": "User session not found"}), 400

    session_id = user_sessions[user_id]["session_id"]
    handle_id = user_sessions[user_id]["handle_id"]
    trans_id=transaction_id()
    # Send answer SDP back to Janus
    answer_request = {
        "janus": "message",
        "body": {
            "request": "start",
            # "room": int(room_id),
            # "offer_audio": False,
            # "offer_video": False
        },
        "jsep": {"type": type, "sdp": sdp},
        "transaction": trans_id,
        "session_id": session_id,
        "handle_id": handle_id
    }
    
    join_response=await janus_request(answer_request)
    if join_response.get("janus") == "ack":
        # Wait for the success response with jsep
        publish_response = await wait_for_janus(JANUS_HTTP_URL+f'/{session_id}', trans_id)
    return jsonify(publish_response)

@app.route('/create_session/<user_id>', methods=['GET'])
async def create_session(user_id):
    if user_id in user_sessions:
        return jsonify({"message": "Session and plugin already created", "session_id": user_sessions[user_id]["session_id"], "handle_id": user_sessions[user_id]["handle_id"]})

    # Step 1: Create a new Janus session
    create_session = {"janus": "create", "transaction":transaction_id()}
    session_response = await janus_request(create_session)
    session_id = session_response["data"]["id"]

    # Step 2: Attach to Video Room plugin
    attach_plugin = {
        "janus": "attach",
        "plugin": "janus.plugin.videoroom",
        "transaction":transaction_id(),
        "session_id": session_id
    }
    plugin_response = await janus_request(attach_plugin)
    handle_id = plugin_response["data"]["id"]

    # Store session and handle for the user
    user_sessions[user_id] = {"session_id": session_id, "handle_id": handle_id}

    return jsonify({"message": "Session and plugin created", "session_id": session_id, "handle_id": handle_id})


@app.route('/rooms')
async def list_rooms():
    user_id = request.args.get('user_id')
    if user_id not in user_sessions:
        return jsonify({"error": "User session not found"}), 400

    session_id = user_sessions[user_id]["session_id"]
    handle_id = user_sessions[user_id]["handle_id"]

    # List all available rooms
    list_rooms_request = {
        "janus": "message",
        "body": {"request": "list"},
        "transaction": transaction_id(),
        "session_id": session_id,
        "handle_id": handle_id
    }
    rooms_response = await janus_request(list_rooms_request)
    rooms = rooms_response["plugindata"]["data"]["list"]

    return jsonify({"rooms": rooms})

@app.route('/create_room', methods=['GET'])
async def create_room():
    user_id = request.args.get('user_id')
    if user_id not in user_sessions:
        return jsonify({"error": "User session not found"}), 400

    session_id = user_sessions[user_id]["session_id"]
    handle_id = user_sessions[user_id]["handle_id"]

    # Create the room with a unique ID or provided settings
    create_room_request = {
        "janus": "message",
        "body": {
            "request": "create",
            "room": 1234, 
            "description": "New Video Room",
            "publishers": 10
        },
        "transaction": transaction_id(),
        "session_id": session_id,
        "handle_id": handle_id
    }
    room_response = await janus_request(create_room_request)
    room = room_response["plugindata"]["data"]

    return jsonify(room)


# Route to get information about a specific video room
@app.route('/room_info/<int:room_id>', methods=['GET'])
async def room_info(room_id):
    user_id = request.args.get('user_id')
    if user_id not in user_sessions:
        return jsonify({"error": "User session not found"}), 400

    session_id = user_sessions[user_id]["session_id"]
    handle_id = user_sessions[user_id]["handle_id"]

    # Request list of participants in the specified room
    list_participants = {
        "janus": "message",
        "body": {
            "request": "listparticipants",
            "room": room_id
        },
        "transaction": transaction_id(),
        "session_id": session_id,
        "handle_id": handle_id
    }
    participants_response = await janus_request(list_participants)
    participants = participants_response["plugindata"]["data"]

    return jsonify({"room": room_id, "participants": participants})


# Main HTML page
@app.route('/<room_id>')
def index(room_id):
    return render_template('index.html', room_id=room_id)

if __name__ == '__main__':
    app.run(debug=True, port=2525)
