#!/usr/bin/env python3
"""
Simple WebSocket test to verify the backend is working
"""

import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection and basic functionality."""
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")
            
            # Test join event
            join_event = {
                "type": "join",
                "room_id": "test-room",
                "name": "TestPlayer",
                "is_bot": False
            }
            
            print(f"Sending join event: {join_event}")
            await websocket.send(json.dumps(join_event))
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received response: {response}")
            
            # Test start event
            start_event = {
                "type": "start"
            }
            
            print(f"Sending start event: {start_event}")
            await websocket.send(json.dumps(start_event))
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received response: {response}")
            
            print("✅ WebSocket test completed successfully!")
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_websocket()) 