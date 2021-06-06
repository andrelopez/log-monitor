from cron_validator import CronValidator


def is_valid(expression: str) -> bool:
    if not expression:
        return False

    _input = expression.split()

    if len(_input) < 6:
        return False

    try:
        CronValidator.parse(" ".join(_input[:5]))
    except ValueError:
        return False

    return True