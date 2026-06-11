import json
import redis
import threading
import time


class ServiceRegistry:
    """Redis-based service registry for microservice discovery."""

    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0, ttl=30):
        self.redis_client = redis.Redis(
            host=redis_host, port=redis_port, db=redis_db, decode_responses=True
        )
        self.ttl = ttl
        self._heartbeat_threads = {}

    def register(self, service_name, host, port):
        key = f"service:{service_name}:{host}:{port}"
        value = json.dumps({
            'name': service_name,
            'host': host,
            'port': port,
            'status': 'up',
        })
        self.redis_client.setex(key, self.ttl, value)
        self._start_heartbeat(service_name, host, port)

    def deregister(self, service_name, host, port):
        key = f"service:{service_name}:{host}:{port}"
        self.redis_client.delete(key)
        thread_key = f"{service_name}:{host}:{port}"
        if thread_key in self._heartbeat_threads:
            self._heartbeat_threads[thread_key]['stop'] = True
            del self._heartbeat_threads[thread_key]

    def discover(self, service_name):
        pattern = f"service:{service_name}:*"
        keys = self.redis_client.keys(pattern)
        services = []
        for key in keys:
            data = self.redis_client.get(key)
            if data:
                services.append(json.loads(data))
        return services

    def get_service_url(self, service_name):
        services = self.discover(service_name)
        if not services:
            return None
        svc = services[0]
        return f"http://{svc['host']}:{svc['port']}"

    def heartbeat(self, service_name, host, port):
        key = f"service:{service_name}:{host}:{port}"
        self.redis_client.expire(key, self.ttl)

    def _start_heartbeat(self, service_name, host, port):
        thread_key = f"{service_name}:{host}:{port}"
        if thread_key in self._heartbeat_threads:
            return
        state = {'stop': False}
        self._heartbeat_threads[thread_key] = state

        def _beat():
            while not state['stop']:
                try:
                    self.heartbeat(service_name, host, port)
                except Exception:
                    pass
                time.sleep(self.ttl // 3)

        t = threading.Thread(target=_beat, daemon=True)
        t.start()
