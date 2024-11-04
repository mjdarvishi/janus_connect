import cv2
import asyncio
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole

SERVER_URL = "http://localhost:2525"
ROOM_ID = 1234
USER_ID = "2"

pc = RTCPeerConnection()
async def display_video(track):
    window_name = "Janus Video Room"
    window_width, window_height = 640, 480 
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL) 
    cv2.resizeWindow(window_name, window_width, window_height)
    while True:
        try:
            frame = await track.recv()
            image = frame.to_ndarray(format="bgr24") 
            cv2.imshow("Janus Video Room", image)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        except Exception as e:
            print(f"Error receiving video frame: {e}")
            break

async def subscribe_to_room():
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/subscribe/{ROOM_ID}?user_id={USER_ID}") as response:
            if response.status != 200:
                print("Failed to subscribe to room")
                return
            
            sdp_offer = await response.json()

        await pc.setRemoteDescription(RTCSessionDescription(sdp_offer['sdp'], sdp_offer['type']))
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        async with session.post(f"{SERVER_URL}/complete_connection", json={
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "room_id": ROOM_ID,
            "user_id": USER_ID
        }) as complete_response:
            if complete_response.status != 200:
                print("Failed to complete connection with Janus")
                return
            print("Joined the room successfully!")

@pc.on("track")
async def on_track(track):
    if isinstance(track, type(pc.getReceivers()[0].track)):  
        print("Incoming video track received")
        asyncio.create_task(display_video(track))
    else:
        print(type(track))

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
