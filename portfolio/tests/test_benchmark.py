import pytest

from portfolio.benchmark import TASKS, evaluate_source


@pytest.mark.parametrize(("task",), [(task,) for task in TASKS])
def test_grader_distinguishes_bug_and_fix(task):
    assert not evaluate_source(task.buggy, task, trusted_fixture=True)["resolved"]
    assert evaluate_source(task.repair, task, trusted_fixture=True)["resolved"]


def test_fix_without_regression_is_rejected():
    result = evaluate_source("def average(values):\n    return None if not values else 0\n", TASKS[0], trusted_fixture=True)
    assert result["suites"]["fix"]["passed"]
    assert not result["suites"]["regression"]["passed"]
    assert not result["resolved"]


def test_external_source_not_executed_locally():
    with pytest.raises(ValueError):
        evaluate_source("raise RuntimeError('must not run')", TASKS[0])
