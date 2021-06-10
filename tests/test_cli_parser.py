import unittest
from click.testing import CliRunner
from src.cli import cli


class TestLogMonitor(unittest.TestCase):

    def test_log_monitor(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["/Users/andre/Documents/log-monitor/sample_csv.txt"])
        self.assertEqual(0, result.exit_code)
        self.assertIn('Find: 3 sample', result.output)


if __name__ == '__main__':
    unittest.main()
