import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import decode_access_token
from app.core.redis import redis_client
from app.models.file import File, FileStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["WebSocket Progress"])


@router.websocket("/ws/{file_id}")
async def websocket_progress(
    websocket: WebSocket,
    file_id: str,
):
    """
    WebSocket endpoint for real-time file verification progress streaming.
    Authenticates via first-message token (not query parameter) to avoid
    token leaking in server access logs, proxy logs, and browser history.
    """
    await websocket.accept()
    logger.info(f"WebSocket connection request for File ID: {file_id}")

    # 1. Wait for auth message from client (timeout 5 seconds)
    try:
        auth_msg_raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        auth_data = json.loads(auth_msg_raw)
        if auth_data.get("type") != "auth":
            await websocket.send_json({"error": "First message must be auth type"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        token = auth_data.get("token")
    except asyncio.TimeoutError:
        logger.warning(f"WebSocket rejected for File ID {file_id}: Auth timeout")
        await websocket.send_json({"error": "Authentication timeout"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    except Exception as e:
        logger.warning(f"WebSocket rejected for File ID {file_id}: {e}")
        await websocket.send_json({"error": "Invalid auth message"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not token:
        logger.warning(f"WebSocket rejected for File ID {file_id}: Missing token")
        await websocket.send_json({"error": "Missing authentication token"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(token)
    if payload is None:
        logger.warning(f"WebSocket rejected for File ID {file_id}: Invalid token")
        await websocket.send_json({"error": "Invalid or expired token"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload.get("sub")
    if not user_id:
        logger.warning(f"WebSocket rejected for File ID {file_id}: Missing sub in token")
        await websocket.send_json({"error": "Invalid token payload"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Get initial state from database
    try:
        async with async_session_maker() as db:
            file_record = await db.get(File, file_id)
            if not file_record:
                logger.warning(f"WebSocket File ID {file_id} not found in database")
                await websocket.send_json({"error": "File not found"})
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                return

            # Check if file has already completed or failed
            current_status = file_record.status.value if file_record.status else "pending"
            current_progress = file_record.verification_progress or 0

            # Send initial progress state
            await websocket.send_json({
                "file_id": file_id,
                "progress": current_progress,
                "status": current_status,
                "current_step": "已建立校验通道，正在同步实时进度..." if current_progress < 100 else "校验已完成。"
            })

            # If already finished, close WebSocket connection cleanly
            if current_status in [FileStatus.COMPLETED.value, FileStatus.WARNING.value, FileStatus.FAILED.value]:
                logger.info(f"WebSocket for File ID {file_id} closed immediately: Already finished (status: {current_status})")
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                return
    except Exception as db_err:
        logger.error(f"Error fetching initial DB state for WebSocket: {db_err}")
        await websocket.send_json({"error": "Database error"})
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # 3. Connect to Redis PubSub and stream updates
    pubsub = None
    channel_name = f"file_progress:{file_id}"
    logger.info(f"Subscribing to Redis channel {channel_name} for WebSocket client")

    try:
        if not redis_client.redis:
            await redis_client.connect()

        pubsub = redis_client.redis.pubsub()
        await pubsub.subscribe(channel_name)

        while True:
            # Poll Pub/Sub message with a timeout so we don't hang indefinitely
            # and can react to connection failures
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                logger.debug(f"Received PubSub message on {channel_name}: {data}")

                # Forward progress data to client
                await websocket.send_json(data)

                # Close connection if completed or failed
                if data.get("progress", 0) >= 100 or data.get("status") in [
                    FileStatus.COMPLETED.value,
                    FileStatus.WARNING.value,
                    FileStatus.FAILED.value,
                ]:
                    logger.info(f"WebSocket verification finished for File ID {file_id}. Closing connection.")
                    break

            # Send a micro-ping occasionally to verify connection is alive
            # If the client closed the connection, this will raise a WebSocketDisconnect exception
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for File ID {file_id}")
    except Exception as e:
        logger.error(f"WebSocket error for File ID {file_id}: {e}")
        try:
            await websocket.send_json({"error": f"Internal server error: {str(e)}"})
        except Exception:
            pass
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
                logger.info(f"Cleaned up Redis PubSub subscription for {channel_name}")
            except Exception as cleanup_err:
                logger.warning(f"Error cleaning up WebSocket PubSub: {cleanup_err}")
        
        # Ensure we try to close connection if it's still open
        try:
            await websocket.close()
        except Exception:
            pass
