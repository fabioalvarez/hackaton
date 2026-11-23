"""What a check is and what it reports.

A *requirement* says what is checked and its criterion, once. A *check* is the function that tests
one or more requirements and returns their results.
"""

from dataclasses import dataclass, field


@dataclass
class Result:
    id: str                 # RF-01, QA-02, CT-01...
    title: str
    expected: str           # the criterion, as the design states it
    measured: str           # what was observed
    passed: bool
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    criterion: str

    def result(self, measured: str, passed: bool, evidence: list[str] | None = None) -> Result:
        return Result(self.id, self.title, self.criterion, measured, passed, evidence or [])


def check(*requirements: Requirement, changes_environment: bool = False, needs_environment: bool = True):
    """Marks a function as the check of these requirements.

    changes_environment: it kills containers, breaks the data, deploys or takes everything down.
    needs_environment:   it needs the environment to be up before it starts (`make up`).
    """
    def mark(function):
        function.requirements = requirements
        function.ids = tuple(requirement.id for requirement in requirements)
        function.changes_environment = changes_environment
        function.needs_environment = needs_environment
        return function

    return mark
