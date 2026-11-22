"""What a check reports."""

from dataclasses import dataclass, field


@dataclass
class Result:
    id: str                 # RF-01, QA-02, CT-01...
    title: str
    expected: str           # the criterion, as the design states it
    measured: str           # what was observed
    passed: bool
    evidence: list[str] = field(default_factory=list)


def covers(*ids: str):
    """Marks which requirements a check function reports on, so `--only` can pick it."""
    def mark(function):
        function.ids = ids
        return function

    return mark
