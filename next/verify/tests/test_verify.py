"""The pure parts of the verification tool: what it parses, counts and reports."""

from datetime import datetime, timezone

from checks_constraints import find_secrets
from report import markdown
from result import Result
from system import Response, down_events, success_rate


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
    responses = [Response(200)] * 98 + [Response(503), Response(0)]

    assert success_rate(responses) == 0.98


def test_success_rate_of_no_responses_is_zero():
    assert success_rate([]) == 0


def test_instance_id_is_read_from_a_lowercase_header():
    assert Response(200, {"x-instance-id": "abc123"}).instance == "abc123"


def test_secrets_are_found():
    # Built here, piece by piece, so this file does not contain what the scanner looks for.
    assert find_secrets("AWS_KEY=" + "AKIA" + "ABCDEFGHIJKLMNOP")
    assert find_secrets("-----BEGIN " + "RSA PRIVATE KEY-----")
    assert find_secrets("pass" + 'word = "hunter2' + 'hunter2"')


def test_normal_text_has_no_secrets():
    assert find_secrets("DATA_PATH=/data/orders.json\nPORT=8080\nLOG_LEVEL=info\n# password: see the vault") == []


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


# --- What is shown live ------------------------------------------------------

from live import describe_backup, describe_event, describe_haproxy  # noqa: E402


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
