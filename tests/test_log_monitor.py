import unittest
import os
from src.service.agent import Agent
from src.model.server import ServerStateMachine, ServerState
from src.event.event import StateChangeEvent
import time
from unittest import mock

TEST_HIGH_TRAFFIC_AND_RECOVERED = os.path.join(os.path.dirname(__file__), 'fixtures/sample_with_high_traffic_and_recovered_alarms.csv')
TEST_ONLY_HIGH_TRAFFIC = os.path.join(os.path.dirname(__file__), 'fixtures/sample_with_only_high_traffic_alarms.csv')


class TestLogMonitor(unittest.TestCase):

    @mock.patch('src.config.ALERT_INTERVAL', 120)
    @mock.patch('src.config.THRESHOLD', 10)
    @mock.patch('src.config.LOG_DELAY', 5)
    def test_should_raise_high_traffic_and_recovered_alarms(self):
        state_events = []

        def on_change_state(event):
            if isinstance(event, StateChangeEvent):
                state_events.append(event)

        server_state_machine = ServerStateMachine()
        agent = Agent(TEST_HIGH_TRAFFIC_AND_RECOVERED, server_state_machine)

        agent.add_state_change_subscriber(on_change_state)

        agent.run()

        time.sleep(1)

        self.assertEqual(len(state_events), 4)

        high_alarm_events = [event for event in state_events if event.server_state == ServerState.HIGH_TRAFFIC]
        recovered_alarm_events = [event for event in state_events if event.server_state == ServerState.GOOD]

        self.assertEqual(len(high_alarm_events), 2)
        self.assertEqual(len(recovered_alarm_events), 2)

    @mock.patch('src.config.ALERT_INTERVAL', 120)
    @mock.patch('src.config.THRESHOLD', 10)
    @mock.patch('src.config.LOG_DELAY', 5)
    def test_should_raise_only_high_traffic(self):
        state_events = []

        def on_change_state(event):
            if isinstance(event, StateChangeEvent):
                state_events.append(event)

        server_state_machine = ServerStateMachine()
        agent = Agent(TEST_ONLY_HIGH_TRAFFIC, server_state_machine)

        agent.add_state_change_subscriber(on_change_state)

        agent.run()

        time.sleep(1)

        self.assertEqual(len(state_events), 2)

        high_alarm_events = [event for event in state_events if event.server_state == ServerState.HIGH_TRAFFIC]
        recovered_alarm_events = [event for event in state_events if event.server_state == ServerState.GOOD]

        self.assertEqual(len(high_alarm_events), 1)
        self.assertEqual(len(recovered_alarm_events), 1)


if __name__ == '__main__':
    unittest.main()
