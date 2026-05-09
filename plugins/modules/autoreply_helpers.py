"""
Helper for waiting for messages with timeout (Telethon doesn't have wait_for)
"""
import asyncio

async def wait_for_message(client, callback, timeout=120, incoming=True, from_me=True):
    """
    Wait for a Telegram message with timeout.
    
    Args:
        client: TelegramClient instance
        callback: async function that takes (event) and returns bool (True = success)
        timeout: seconds to wait
        incoming: only incoming messages
        from_me: only messages from authenticated account
        
    Returns:
        event if found, None if timeout
    """
    def _check_message(event):
        if incoming and not event.is_private:
            return False
        if from_me and event.out:
            return False
        return True
    
    # Add new async task for checking messages
    lock = asyncio.Lock()
    result = {'found': None}
    
    def _on_new_message(event):
        if _check_message(event):
            async with lock:
                if result['found'] is None:
                    result['found'] = event
                    # Cancel listener
    
    # Register callback temporarily
    client.add_event_handler(_on_new_message, events.NewMessage(incoming=incoming, func=lambda e: from_me == e.out))
    
    try:
        # Wait for result
        done, pending = await asyncio.wait(
            asyncio.create_task(asyncio.to_thread(asyncio.sleep, timeout)),
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in pending:
            task.cancel()
        
        return result['found']
    except asyncio.CancelledError:
        return None
    finally:
        client.remove_event_handler(_on_new_message, events.NewMessage(incoming=incoming, func=lambda e: from_me == e.out))