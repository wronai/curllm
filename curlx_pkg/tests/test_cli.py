import types
import sys
import curlx.cli as cli


class Args(types.SimpleNamespace):
    pass


def test_register_builds_json(monkeypatch):
    captured = {}

    def fake_post_json(url, data):
        captured['url'] = url
        captured['data'] = data
        return 0

    monkeypatch.setattr(cli, 'post_json', fake_post_json)
    args = Args(host='1.2.3.4', ports='3128, 3129', server='http://api:8000')
    rc = cli.cmd_register(args)
    assert rc == 0
    assert captured['url'].endswith('/api/proxy/register')
    assert captured['data']['proxies'] == [
        'http://1.2.3.4:3128',
        'http://1.2.3.4:3129',
    ]


def test_list_uses_requests(monkeypatch):
    # Force curl not available
    monkeypatch.setenv('PATH', '')

    class DummyResp:
        text = '{"proxies":[],"count":0}'

    def fake_get(url):
        return DummyResp()

    import builtins
    # Inject requests module shim
    requests = types.SimpleNamespace(get=fake_get)
    monkeypatch.setitem(sys.modules, 'requests', requests)

    args = Args(server='http://api:8000')
    rc = cli.cmd_list(args)
    assert rc == 0


def test_spawn_commands(monkeypatch):
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return 0

    def fake_post_json(url, data):
        calls.append(['POST', url, data])
        return 0

    monkeypatch.setattr(cli, 'run', fake_run)
    monkeypatch.setattr(cli, 'post_json', fake_post_json)

    args = Args(host='ubuntu@host.example', ports='3128,3129', server='http://api:8000', python='python3', ssh='ssh')
    rc = cli.cmd_spawn(args)
    assert rc == 0
    # Ensure install and two start commands were issued, plus register
    assert any('pip install' in ' '.join(c) for c in calls)
    assert sum(1 for c in calls if isinstance(c, list) and 'nohup' in ' '.join(c)) == 2
    assert any(isinstance(c, list) and c[0] == 'POST' and c[1].endswith('/api/proxy/register') for c in calls)
