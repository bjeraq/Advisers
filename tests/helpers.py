from datetime import date, timedelta

from advisers.data import Bar


def bars_from_closes(closes):
    start = date(2020, 1, 1)
    return [
        Bar(start + timedelta(days=i), c, c, c, c, 1000)
        for i, c in enumerate(closes)
    ]
