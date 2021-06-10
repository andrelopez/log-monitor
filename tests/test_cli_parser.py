import unittest
from click.testing import CliRunner
from src.cli import cli


class TestLogMonitor(unittest.TestCase):

    def test_test(self):
        self.assertEqual('test', 'test')

    def test_log_monitor(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["/Users/parzival/Documents/Python/log_monitor/sample_csv.txt"])
        self.assertEqual(0, result.exit_code)
        self.assertIn('Find: 3 sample', result.output)


if __name__ == '__main__':
    unittest.main()

# import pytest
# from src import cli
# from click.testing import CliRunner
# from src.utils import utils
#
#
# @pytest.fixture
# def runner():
#     return CliRunner()
#
#
# @pytest.mark.parametrize(('argument', 'output'), [
#     pytest.param('/Users/parzival/Documents/Python/log_monitor/sample_csv.txt', "", id='output')
# ])
# def test_returns_invalid_cron_arguments(runner, argument, output):
#     result = runner.invoke(cli.cli, [argument])
#     assert result.exit_code == 0
#     assert result.output.strip() == output.strip()
