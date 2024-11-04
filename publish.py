import os
import asyncio
import json
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
import cv2,time
from aiortc import  RTCPeerConnection, RTCSessionDescription,RTCConfiguration,RTCIceServer
from fractions import Fraction
from av import VideoFrame
import requests
import os
import asyncio
from aiortc import  VideoStreamTrack
import threading
from datetime import datetime
import sys



class RTSPVideoStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.video_recorder = cv2.VideoCapture('rtsp://admin:Vigilanza2018@192.168.202.201/Streaming/Channels/1')

    async def recv(self):
        current_time = time.time()
        ret, frame = self.video_recorder.read()
        if not ret:
            print("RTSP feed is not accessible.")
            return None
        timestamp_ms = int(current_time * 1000)
        new_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        new_frame.pts = timestamp_ms
        new_frame.time_base = Fraction(1, 90000)
        return new_frame

class WebRtc:
    def __init__(self,) -> None:
        self.thread= threading.Thread(target=self.run_connection,)
        self.stop_event = threading.Event()
        self.created_time=datetime.now()
        self.enable=True
        self.pc = RTCPeerConnection(
              configuration=RTCConfiguration([
                    RTCIceServer(urls="stun:stun.l.google.com:19302"),
                ])
        )
    
    async def create_offer(self):
        @self.pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            print(f"ICE connection state is {self.pc.iceConnectionState}")
            if self.pc.iceConnectionState in ["failed", "closed", "disconnected"]:
                self.enable=False
        self.pc.addTrack(RTSPVideoStreamTrack())
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)


    async def set_answer(self,answer_sdp):
        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=answer_sdp, type="answer"))
        print('connection created successfully')
        while self.enable:
            await asyncio.sleep(1)

    def start(self):
        self.thread.start()
            
    def run_connection(self):
        asyncio.run(self.start())


web_rtc_connection=WebRtc()
        
def handle_shutdown(signum, frame):
    print("Shutdown signal received")
    web_rtc_connection.pc.close()
    web_rtc_connection.stop_event.set()
    sys.exit(0)

        
async def main(web_rtc_connection:WebRtc):
    requests.get('http://127.0.0.1:2525/create_session/1')
    requests.get('http://127.0.0.1:2525/create_session/2')
    # Gather ICE candidates
    await web_rtc_connection.create_offer()    
    res=requests.post('http://localhost:2525/add_track/1234?user_id=1',json={'sdp':web_rtc_connection.pc.localDescription.sdp})
    data=res.json()
    await web_rtc_connection.set_answer(data["sdp"])
    
asyncio.run(main(web_rtc_connection))
