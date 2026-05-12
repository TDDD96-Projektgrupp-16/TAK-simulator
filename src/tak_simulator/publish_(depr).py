import time
import threading

class Receiver:
    def __init__(self, name, id):
        self.name = name
        self.id = id
    def receive(self, sender, message, timestamp):
        print(f"[{timestamp:5.1f}s] {sender} -> {self.name}: {message}")


class ScenarioSender:
    def __init__(self, scenario, receivers):
        self.events = sorted(scenario["messages"], key=lambda x: x[0])
        self.receivers = receivers  # list of Receiver instances
        self._running = False

    def start(self):
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._running = False

    def _run(self):
        start_time = time.time()

        for timestamp, id, sender, message in self.events:
            if not self._running:
                break

            # Wait until it's time
            elapsed = time.time() - start_time
            delay = timestamp - elapsed

            if delay > 0:
                time.sleep(delay)

            # Broadcast to all receivers
            for r in self.receivers:
                if r.id == id:
                    r.receive(sender, message, timestamp)

        print("Scenario finished.")


scenario = {
    "messages": [
        [0, 1, "Algot Johansson", "Jag blir lite sen!"],
        [3, 2,"Arvid Ramsberg", "När kommer du?"],
        [10, 2,"Arvid Ramsberg", "Var är du?"],
        [20, 1, "Algot Johansson", "Så, är framme nu!"],
    ]
}

receivers = [
    Receiver("Console A", 1),
    Receiver("Console B", 2)
]

sender = ScenarioSender(scenario, receivers)
sender.start()

time.sleep(25)