# Http Log Monitor
A http log monitor that will display last stats and raise alarms.

## Usage
Use the following command:
`log-monitor "/path/to/log/file.csv"`

The output will be formatted as a table with a maximum of 14 columns

For example, the following input argument:

```bash
~$ log-monitor ＂/path/to/log/file.csv＂
```

## Installation

Create a new Python 3 environment called venv and activate it (Mac or Linux):

```bash
~$ python3 -m venv ./venv
~$ source ./venv/bin/activate
~$ pip install --editable .
```

### Tests

Tests are managed by [pytest](https://docs.pytest.org/en/6.2.x/contents.html), the tests are under the `test` directory, 
you can run the tests with the following command:

```bash
~$ (venv) pytest tests -v   
```
