import pytest
from src import cli
from click.testing import CliRunner
from src.config import ERROR_INVALID_ARGUMENT
from src.utils import utils


@pytest.fixture
def runner():
    return CliRunner()


@pytest.mark.parametrize(('argument', 'output'), [
    pytest.param('*/15 0 1,15 * 1-5 /usr/bin/find',
                 utils.print_table('0 15 30 45', '0', '1 15', '1 2 3 4 5 6 7 8 9 10 11 12', '1 2 3 4 5',
                                   '/usr/bin/find'),
                 id='Valid with all special chars'),

    pytest.param('*/15    0 1,15 *           1-5                /usr/bin/find',
                 utils.print_table('0 15 30 45', '0', '1 15', '1 2 3 4 5 6 7 8 9 10 11 12', '1 2 3 4 5',
                                   '/usr/bin/find'),
                 id='Valid with all standard cron format with spaces'),

    pytest.param('* * * * * /jarvis/do/this',
                 utils.print_table('0 1 2 3 4 5 6 7 8 9 10 11 12 13', '0 1 2 3 4 5 6 7 8 9 10 11 12 13',
                                   '1 2 3 4 5 6 7 8 9 10 11 12 13 14', '1 2 3 4 5 6 7 8 9 10 11 12', '0 1 2 3 4 5 6',
                                   '/jarvis/do/this'),
                 id='All *'),

    pytest.param('0 0 1 1 0 /jarvis/do/this', utils.print_table('0', '0', '1', '1', '0',
                                                                '/jarvis/do/this'), id='Specific values'),

    pytest.param('0 0 1 1 0 ./first.py && ./second.py', utils.print_table('0', '0', '1', '1', '0',
                                                                          './first.py && ./second.py'),
                 id='Command with spaces'),

    pytest.param('59-2 0 1 1 0 ./command', utils.print_table('59 0 1 2', '0', '1', '1', '0',
                                                                          './command'),
                 id='Range in reverse'),

])
def test_returns_cron_parsed(runner, argument, output):
    result = runner.invoke(cli.cli, [argument])
    assert result.exit_code == 0
    assert result.output.strip() == output.strip()


@pytest.mark.parametrize(('argument', 'output'), [
    pytest.param('*/15 0 1,15 * 1- /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Wrong range'),
    pytest.param('* * * * *', ERROR_INVALID_ARGUMENT, id='Missing command'),
    pytest.param('* * * * *   ', ERROR_INVALID_ARGUMENT, id='Missing command 2'),
    pytest.param('*/ * * * * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Wrong step'),
    pytest.param('*/150 * * * * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Step out of range'),
    pytest.param('*/5 * * * 1,7 /usr/bin/find', ERROR_INVALID_ARGUMENT, id='List out of range'),
    pytest.param('*/5 0 * * 1, /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Wrong list'),
    pytest.param('* /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Wrong cron'),
    pytest.param('* * * * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Wrong cron'),
    pytest.param('* * * B * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Wrong cron'),
    pytest.param('60 * * * * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Minute out of range'),
    pytest.param('* 24 * * * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Hour out of range'),
    pytest.param('* * 32 * * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Day out of range'),
    pytest.param('* * * 13 * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Month out of range'),
    pytest.param('* * * * 7 /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Week out of range'),
    pytest.param('*1 * * * * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Invalid star'),
    pytest.param('** * * * * /usr/bin/find', ERROR_INVALID_ARGUMENT, id='Double star')
])
def test_returns_invalid_cron_arguments(runner, argument, output):
    result = runner.invoke(cli.cli, [argument])
    assert result.exit_code == 0
    assert result.output.strip() == output.strip()
