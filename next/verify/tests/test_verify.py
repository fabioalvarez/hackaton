"""The verification tool: what it declares, reads, counts and reports. (The checks themselves run against the environment.)"""

from datetime import datetime, timezone

import pytest

import checks_constraints
import checks_functional
import checks_quality
import commands
import main
from checks_constraints import find_secrets
from environment import down_events
from report import markdown, sort_key
from result import Requirement, Result, check
from service import Response, parse_json, success_rate
from watching import describe_backup, describe_event, describe_haproxy


# --- What the tool declares ----------------------------------------------------------

def test_every_requirement_is_checked_exactly_once():
    ids = [id for each in main.ALL_CHECKS for id in each.ids]

    assert len(ids) == len(set(ids))
    assert sorted(ids) == ["CT-01", "CT-02", "QA-01", "QA-02", "QA-03", "QA-04", "QA-05", "QA-06", "QA-07",
                           "RF-01", "RF-02", "RF-03", "RF-04", "RF-05", "TESTS"]


def test_every_requirement_has_a_title_and_a_criterion():
    for each in main.ALL_CHECKS:
        for requirement in each.requirements:
            assert requirement.title and requirement.criterion


def test_all_the_quality_scenarios_change_the_environment_and_nothing_else_does():
    assert all(each.changes_environment for each in checks_quality.CHECKS)
    assert not any(each.changes_environment for each in checks_functional.CHECKS + checks_constraints.CHECKS)


def test_the_scenarios_that_bring_the_environment_up_themselves_do_not_need_it_before():
    needing_nothing = {id for each in main.ALL_CHECKS if not each.needs_environment for id in each.ids}

    assert needing_nothing == {"QA-05", "QA-07"}


def test_a_requirement_builds_its_result_with_its_own_title_and_criterion():
    requirement = Requirement("RF-99", "A title", "a criterion")
    result = requirement.result("what was measured", True, ["proof"])

    assert result == Result("RF-99", "A title", "a criterion", "what was measured", True, ["proof"])


def test_the_check_decorator_records_what_the_function_checks():
    first, second = Requirement("QA-91", "t", "c"), Requirement("QA-92", "t", "c")

    @check(first, second, changes_environment=True)
    def together():
        pass

    assert together.ids == ("QA-91", "QA-92") and together.changes_environment and together.needs_environment


def test_a_check_that_breaks_is_reported_as_failed_with_its_requirements():
    requirement = Requirement("RF-99", "A title", "a criterion")

    @check(requirement)
    def broken():
        raise RuntimeError("it broke")

    result = main.attempt(broken)[0]

    assert result.id == "RF-99" and result.passed is False and "it broke" in result.measured


def test_only_picks_the_checks_of_those_ids_and_everything_if_none():
    assert main.choose(None) == main.ALL_CHECKS
    assert [id for each in main.choose("qa-01") for id in each.ids] == ["QA-01", "QA-06"]   # they are the same incident


# --- Reading and counting ------------------------------------------------------------

def test_down_events_are_read_from_the_haproxy_log_in_utc():
    log = (
        "2026-11-22T18:05:52.788123456Z [WARNING]  (8) : Server api/api1 is DOWN, reason: Layer4 timeout\n"
        "2026-11-22T18:05:53.100000000Z 192.168.65.1:1 [22/Nov/2026:18:05:53.100] web api/api2 0/0/0/2/2 200 500\n"
        "2026-11-22T18:05:59Z Server api/api2 is going DOWN for maintenance (No IP for server )\n"
    )
    first, second = down_events(log)

    assert first == datetime(2026, 11, 22, 18, 5, 52, 788123, tzinfo=timezone.utc).timestamp()
    assert second == datetime(2026, 11, 22, 18, 5, 59, tzinfo=timezone.utc).timestamp()


def test_other_servers_going_down_are_not_counted():
    assert down_events("2026-11-22T18:05:52Z Server other/x is DOWN") == []


def test_success_rate_counts_only_200s():
    assert success_rate([Response(200)] * 98 + [Response(503), Response(0)]) == 0.98
    assert success_rate([]) == 0


def test_a_response_reads_its_instance_and_version_from_lowercase_headers():
    response = Response(200, {"x-instance-id": "abc123", "x-data-version": "v1"})

    assert response.instance == "abc123" and response.version == "v1"


def test_a_page_that_is_not_json_has_no_body():
    assert parse_json("<html></html>") is None
    assert parse_json('{"a": 1}') == {"a": 1}


# --- Secrets -------------------------------------------------------------------------

def test_secrets_are_found():
    # Built here, piece by piece, so this file does not contain what the scanner looks for.
    assert find_secrets("AWS_KEY=" + "AKIA" + "ABCDEFGHIJKLMNOP")
    assert find_secrets("-----BEGIN " + "RSA PRIVATE KEY-----")
    assert find_secrets("pass" + 'word = "hunter2' + 'hunter2"')


def test_normal_text_has_no_secrets():
    assert find_secrets("DATA_PATH=/data/orders.json\nPORT=8080\nLOG_LEVEL=info\n# password: see the vault") == []


# --- The report ----------------------------------------------------------------------

def test_the_report_lists_every_result_and_the_total():
    results = [
        Result("RF-01", "Consultar pedidos", "6 pedidos", "6 pedidos", True),
        Result("QA-01", "Una instancia falla", "≥ 99 %", "90 %", False, ["la instancia abc fue detenida"]),
    ]
    text = markdown(results, datetime(2026, 11, 22, 18, 0, 0))

    assert "**1 de 2 cumplen**" in text
    assert "| RF-01 | Consultar pedidos | 6 pedidos | 6 pedidos | CUMPLE |" in text
    assert "| QA-01 | Una instancia falla | ≥ 99 % | 90 % | NO CUMPLE |" in text
    assert "- la instancia abc fue detenida" in text


def test_results_are_sorted_functional_then_constraints_then_tests_then_quality():
    results = [Result(id, "t", "c", "m", True) for id in ("QA-02", "TESTS", "CT-01", "RF-05", "QA-01")]

    assert [r.id for r in sorted(results, key=sort_key)] == ["RF-05", "CT-01", "TESTS", "QA-01", "QA-02"]


# --- Versions ------------------------------------------------------------------------

def test_next_version_follows_the_last_numbered_one(tmp_path, monkeypatch):
    (tmp_path / ".deploy-history").write_text("1.5.0\nv1\nv2\nweird\n")
    monkeypatch.setattr(commands, "ROOT", tmp_path)

    assert commands.next_version() == "v3"


def test_the_first_version_is_v1_and_the_current_one_is_dev(tmp_path, monkeypatch):
    monkeypatch.setattr(commands, "ROOT", tmp_path)

    assert commands.next_version() == "v1" and commands.current_tag() == "dev"


def test_an_empty_history_means_dev(tmp_path, monkeypatch):
    (tmp_path / ".deploy-history").write_text("")
    monkeypatch.setattr(commands, "ROOT", tmp_path)

    assert commands.current_tag() == "dev"


# --- What is told while the checks run -------------------------------------------------

def test_container_events_are_described_in_words():
    assert describe_event("die|next-api-1") == ("🔻", "api-1 se detuvo")
    assert describe_event("start|next-api-3") == ("🟢", "api-3 arrancó")
    assert describe_event("health_status: healthy|next-api-3") == ("💚", "api-3 está sano")
    assert describe_event("health_status: unhealthy|next-api-3") == ("💔", "api-3 dejó de estar sano")


def test_events_of_other_containers_and_actions_are_ignored():
    assert describe_event("die|some-other-container") is None
    assert describe_event("exec_start: sh|next-api-1") is None


def test_haproxy_lines_about_its_servers_are_described():
    down = "Server api/api1 is DOWN, reason: Layer7 wrong status, code: 503, info: x, check duration: 4ms."
    gone = "Server api/api2 is going DOWN for maintenance (No IP for server ). 1 active"
    found = "Server api/api3 ('api') is UP/READY (resolves again)."
    up = "Server api/api3 is UP, reason: Layer7 check passed, code: 200, check duration: 2ms."

    assert describe_haproxy(down) == ("🔻", "HAProxy: saca una instancia de la rotación (Layer7 wrong status)")
    assert describe_haproxy(gone)[1].startswith("HAProxy: una instancia ya no existe")
    assert describe_haproxy(found)[1].startswith("HAProxy: encontró una instancia nueva")
    assert describe_haproxy(up)[1] == "HAProxy: una instancia responde, entra a la rotación"


def test_haproxy_lines_about_requests_are_ignored():
    assert describe_haproxy('192.168.65.1:1 [22/Nov/2026:18:05:53.100] web api/api2 0/0/0/2/2 200 500 "GET /orders"') is None


def test_the_backup_watcher_shows_what_it_does_but_not_what_it_checks():
    assert describe_backup('{"level": "info", "detail": "restore done in 0.0s"}') == ("💾", "vigilante: restore done in 0.0s")
    assert describe_backup('{"level": "error", "detail": "no backup"}')[0].startswith("⚠")
    assert describe_backup('{"level": "debug", "detail": "starting backup process"}') is None
    assert describe_backup("not json") is None
