# JanusConnect

**JanusConnect** is a Python-based wrapper that simplifies the integration of the Janus WebRTC server with easy-to-use APIs. Built with Flask and aiohttp, this project enables quick setup and interaction with Janus for video publishing and subscribing in WebRTC applications.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [License](#license)

## Overview
JanusConnect provides an easy interface for managing video rooms, sessions, and streams with Janus WebRTC. This project includes three components:
- **Server**: The core Flask application that communicates with the Janus server.
- **Publisher**: A client script that acts as a video publisher.
- **Subscriber**: A client script that subscribes to published video feeds.

## Features
- **Room Management**: Create and list video rooms.
- **Session Management**: Start and manage sessions.
- **Publishing and Subscribing**: Publish video tracks to a room and subscribe to available feeds.
- **Flask API**: Expose endpoints for managing rooms, tracks, and subscriptions.
- **Async Support**: Fully asynchronous operations with aiohttp for non-blocking communication with Janus.

## Architecture
JanusConnect uses Flask for the API server, which acts as an intermediary between clients and the Janus WebRTC server. Video publishing and subscribing are implemented using `aiortc`, which provides WebRTC peer-to-peer connection capabilities. 

The Flask server (`server.py`) handles API requests and interacts with Janus through HTTP and WebRTC messages. `Publisher.py` and `Subscriber.py` demonstrate client interactions, allowing for easy expansion into various WebRTC applications.

## Getting Started
### Prerequisites
- Python 3.8+
- [Janus WebRTC Server](https://janus.conf.meetecho.com/)
- Dependencies: Install via `pip install -r requirements.txt`

### Installation
1. Clone this repository.
    ```bash
    git clone https://github.com/yourusername/JanusConnect.git
    cd JanusConnect
    ```
2. Install the dependencies.
    ```bash
    pip install -r requirements.txt
    ```
3. Start the Janus server locally or configure `JANUS_HTTP_URL` in `server.py` to point to your Janus instance.

### Running
Start the Flask server on port 2525:
```bash
python server.py

# Running publisher
python publisher.py


# Running subscriber
python subscriber.py
