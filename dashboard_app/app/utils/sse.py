import gevent
from gevent.queue import Queue

class MessageAnnouncer:
    def __init__(self):
        self.listeners = []

    def listen(self):
        q = Queue(maxsize=5)
        self.listeners.append(q)
        return q

    def announce(self, msg, event="datachanged"):
        # Slight delay to ensure DB transactions are finalized and visible to other processes
        gevent.sleep(0.5)

        # Format for SSE: "event: <event>\ndata: <msg>\n\n"
        sse_msg = f"event: {event}\ndata: {msg}\n\n"
        
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(sse_msg)
            except Exception:
                # Remove stale listeners (e.g., disconnected clients)
                del self.listeners[i]

# Global instance
announcer = MessageAnnouncer()
