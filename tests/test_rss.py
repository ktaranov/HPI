from more_itertools import ilen

import my.rss


def test_rss() -> None:
    assert ilen(my.rss.subscription_history()) >= 1
    computes = list(my.rss.events())
    assert {True, False} == set([r.added for r in computes])
