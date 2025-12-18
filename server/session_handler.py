import asyncio
import base64
import json

from context import clear_session_handler, set_session_handler
from core_utils import SEND_SAMPLE_RATE, stream_logger
from orchestrator import SessionOrchestrator


class ClientSessionHandler:
    """
    Handles the lifecycle of a single client connection session.
    Encapsulates connection-specific state, queues, and task coordination.
    """

    def __init__(self, websocket, session_orchestrator: SessionOrchestrator, client_id):
        self.websocket = websocket
        self.session_orchestrator = session_orchestrator
        self.client_id = client_id
        self.audio_queue = asyncio.Queue()
        self.video_queue = asyncio.Queue()

    async def run(self):
        """Starts all concurrent tasks for handling the client session."""
        # Set context for this session so tools can access the WebSocket
        set_session_handler(self)
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._receive_client_messages(), name="ClientMessageReceiver")
                tg.create_task(self._send_audio_to_service(), name="AudioSender")
                tg.create_task(self._send_video_to_service(), name="VideoSender")
                tg.create_task(self._receive_service_responses(), name="ServiceResponseReceiver")
        finally:
            # Clear context when session ends
            clear_session_handler()

    async def send_ui_message(self, message_type: str, data: dict):
        """
        Helper method to send UI-related messages to the client.

        Args:
            message_type: The type of UI message (e.g., 'ui_content', 'ui_card', 'ui_list')
            data: The data payload to send
        """
        try:
            message = json.dumps({"type": message_type, "data": data})
            await self.websocket.send(message)
        except Exception as e:
            stream_logger.error(f"Error sending UI message: {e}")

    async def _receive_client_messages(self):
        """Process incoming WebSocket messages from the client."""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "audio":
                    audio_bytes = base64.b64decode(data.get("data", ""))
                    await self.audio_queue.put(audio_bytes)
                elif data.get("type") == "video":
                    video_bytes = base64.b64decode(data.get("data", ""))
                    video_mode = data.get("mode", "webcam")
                    await self.video_queue.put({"data": video_bytes, "mode": video_mode})
                elif data.get("type") == "end":
                    stream_logger.info("Client has concluded data transmission for this turn.")
                elif data.get("type") == "text":
                    stream_logger.info(f"Received text from client: {data.get('data')}")
            except json.JSONDecodeError:
                stream_logger.error("Could not decode incoming JSON message.")
            except Exception as e:
                stream_logger.error(f"Exception while processing client message: {e}")

    async def _send_audio_to_service(self):
        """Sends audio data from the queue to the session orchestrator."""
        while True:
            data = await self.audio_queue.get()
            self.session_orchestrator.send_audio(data, SEND_SAMPLE_RATE)
            self.audio_queue.task_done()

    async def _send_video_to_service(self):
        """Sends video data from the queue to the session orchestrator."""
        while True:
            video_data = await self.video_queue.get()
            video_bytes = video_data.get("data")
            video_mode = video_data.get("mode", "webcam")
            stream_logger.info(f"Transmitting video frame from source: {video_mode}")
            self.session_orchestrator.send_video(video_bytes)
            self.video_queue.task_done()

    async def _receive_service_responses(self):
        """Processes responses from the agent and sends them to the client."""
        # Track user and model outputs between turn completion events
        input_texts = []
        output_texts = []
        current_session_id = None

        # Flag to track if we've seen an interruption in the current turn
        interrupted = False

        # Process responses from the agent via orchestrator
        async for event in await self.session_orchestrator.stream_responses():
            # Check for turn completion or interruption using string matching
            event_str = str(event)

            # If there's a session resumption update, store the session ID
            if hasattr(event, "session_resumption_update") and event.session_resumption_update:
                update = event.session_resumption_update
                if update.resumable and update.new_handle:
                    current_session_id = update.new_handle
                    stream_logger.info(f"Established new session with handle: {current_session_id}")
                    # Send session ID to client
                    session_id_msg = json.dumps({"type": "session_id", "data": current_session_id})
                    await self.websocket.send(session_id_msg)

            # Handle content
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # Process audio content
                    if hasattr(part, "inline_data") and part.inline_data:
                        b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                        await self.websocket.send(json.dumps({"type": "audio", "data": b64_audio}))

                    # Process text content
                    if hasattr(part, "text") and part.text:
                        # Check if this is user or model text based on content role
                        if hasattr(event.content, "role") and event.content.role == "user":
                            # User text should be sent to the client
                            if "partial=True" in event_str:
                                await self.websocket.send(json.dumps({"type": "user_transcript", "data": part.text}))
                            input_texts.append(part.text)
                        else:
                            # Streaming chunks with "partial=True"
                            if "partial=True" in event_str:
                                await self.websocket.send(json.dumps({"type": "text", "data": part.text}))
                                output_texts.append(part.text)

            # Check for interruption
            if event.interrupted and not interrupted:
                stream_logger.warning("User has interrupted the stream.")
                await self.websocket.send(
                    json.dumps({"type": "interrupted", "data": "Response interrupted by user input"})
                )
                interrupted = True

            # Check for turn completion
            if event.turn_complete:
                # Only send turn_complete if there was no interruption
                if not interrupted:
                    stream_logger.info("The model has completed its turn.")
                    await self.websocket.send(json.dumps({"type": "turn_complete", "session_id": current_session_id}))

                # Log collected transcriptions for debugging
                if input_texts:
                    unique_texts = list(dict.fromkeys(input_texts))
                    stream_logger.info(f"Transcribed user speech: {' '.join(unique_texts)}")

                if output_texts:
                    unique_texts = list(dict.fromkeys(output_texts))
                    stream_logger.info(f"Generated model response: {' '.join(unique_texts)}")

                # Reset for next turn
                input_texts = []
                output_texts = []
                interrupted = False
