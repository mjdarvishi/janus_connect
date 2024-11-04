import cv2
import asyncio
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole

# Configuration for Janus
JANUS_URL = "http://localhost:2525"
ROOM_ID = 1234
USER_ID = "2"

# WebRTC setup with aiortc
pc = RTCPeerConnection()
blackhole = MediaBlackhole()  # To handle audio tracks if needed

# Display the incoming video frames using OpenCV
async def display_video(track):
    window_name = "Janus Video Room"
    window_width, window_height = 640, 480  # Set your desired size here
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)  # Create a resizable window
    cv2.resizeWindow(window_name, window_width, window_height)  # Set window size
    while True:
        try:
            # Receive and display frames
            frame = await track.recv()
            image = frame.to_ndarray(format="bgr24")  # Convert frame to OpenCV format
            cv2.imshow("Janus Video Room", image)

            # Exit display loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        except Exception as e:
            print(f"Error receiving video frame: {e}")
            break

async def subscribe_to_room():
    async with aiohttp.ClientSession() as session:
        # Step 1: Send a subscription request to Janus
        async with session.post(f"{JANUS_URL}/subscribe/{ROOM_ID}?user_id={USER_ID}") as response:
            if response.status != 200:
                print("Failed to subscribe to room")
                return
            
            sdp_offer = await response.json()

        # Step 2: Set the remote description with Janus' SDP offer
        await pc.setRemoteDescription(RTCSessionDescription(sdp_offer['sdp'], sdp_offer['type']))
        
        # Step 3: Create an SDP answer and set it as the local description
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        # Step 4: Send the SDP answer back to Janus
        async with session.post(f"{JANUS_URL}/complete_connection", json={
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "room_id": ROOM_ID,
            "user_id": USER_ID
        }) as complete_response:
            if complete_response.status != 200:
                print("Failed to complete connection with Janus")
                return
            print("Joined the room successfully!")

# Handle incoming video tracks
@pc.on("track")
async def on_track(track):
    if isinstance(track, type(pc.getReceivers()[0].track)):  # Check if it's a RemoteStreamTrack
        print("Incoming video track received")
        # Start displaying video in a separate task immediately when track arrives
        asyncio.create_task(display_video(track))
    else:
        print(type(track))

# Run the connection and video display
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(subscribe_to_room())
        loop.run_forever()
    except KeyboardInterrupt:
        print("Exiting")
    finally:
        loop.run_until_complete(pc.close())
        cv2.destroyAllWindows()
