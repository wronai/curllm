#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from typing import List

API_HOST_DEFAULT = os.getenv("CURLLM_API_HOST", "http://localhost:8000")
SSH_BIN_DEFAULT = os.getenv("SSH_BIN", "ssh")
PY_BIN_REMOTE_DEFAULT = os.getenv("PY_BIN_REMOTE", "python3")


def run(cmd: List[str]) -> int:
    return subprocess.call(cmd)


def post_json(url: str, data: dict | str) -> int:
    # Avoid extra deps; use curl if available, else python requests fallback
    if os.system("command -v curl >/dev/null 2>&1") == 0:
        payload = data if isinstance(data, str) else json.dumps(data)
        p = subprocess.Popen(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                url,
                "-H",
                "Content-Type: application/json",
                "-d",
                payload,
            ]
        )
        return p.wait()
    else:
        try:
            import requests  # type: ignore
        except Exception:
            print("requests not installed; please install or provide curl command", file=sys.stderr)
            return 1
        try:
            if isinstance(data, str):
                r = requests.post(url, data=data, headers={"Content-Type": "application/json"})
            else:
                r = requests.post(url, json=data)
            sys.stdout.write(r.text)
            return 0
        except Exception as e:
            print(f"POST failed: {e}", file=sys.stderr)
            return 1


def cmd_register(args: argparse.Namespace) -> int:
    if not args.host or not args.ports:
        print("--host and --ports required", file=sys.stderr)
        return 1
    ports = [p.strip() for p in args.ports.split(",") if p.strip()]
    proxies = [f"http://{args.host}:{p}" for p in ports]
    data = {"proxies": proxies}
    return post_json(f"{args.server}/api/proxy/register", data)


def cmd_list(args: argparse.Namespace) -> int:
    url = f"{args.server}/api/proxy/list"
    if os.system("command -v curl >/dev/null 2>&1") == 0:
        return run(["curl", "-s", url])
    else:
        try:
            import requests  # type: ignore
        except Exception:
            print("requests not installed; please install or provide curl command", file=sys.stderr)
            return 1
        try:
            r = requests.get(url)
            sys.stdout.write(r.text)
            return 0
        except Exception as e:
            print(f"GET failed: {e}", file=sys.stderr)
            return 1


def cmd_spawn(args: argparse.Namespace) -> int:
    if not args.host or not args.ports:
        print("--host and --ports required", file=sys.stderr)
        return 1
    ssh = args.ssh or SSH_BIN_DEFAULT
    py = args.python or PY_BIN_REMOTE_DEFAULT
    ports = [p.strip() for p in args.ports.split(",") if p.strip()]

    # Install proxy.py on remote
    rc = run([ssh, args.host, f"{py} -m pip install --user -q proxy.py || true"])
    if rc != 0:
        return rc
    # Start proxies
    for p in ports:
        cmd = f"nohup {py} -m proxy --hostname 0.0.0.0 --port {p} >/tmp/proxy_{p}.log 2>&1 & echo $! > /tmp/proxy_{p}.pid"
        rc = run([ssh, args.host, cmd])
        if rc != 0:
            return rc
    # Register
    host_only = args.host.split("@")[-1]
    proxies = [f"http://{host_only}:{p}" for p in ports]
    data = {"proxies": proxies}
    # Pass JSON string so downstream join on test harness doesn't fail
    return post_json(f"{args.server}/api/proxy/register", json.dumps(data))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="curlx", description="curlx - Proxy helper for curllm")
    sub = p.add_subparsers(dest="sub")

    p_reg = sub.add_parser("register", help="Register existing proxies")
    p_reg.add_argument("--host", required=True, help="Proxy host/IP")
    p_reg.add_argument("--ports", required=True, help="Comma-separated ports, e.g. 3128,3129")
    p_reg.add_argument("--server", default=API_HOST_DEFAULT, help="curllm API host")
    p_reg.set_defaults(func=cmd_register)

    p_list = sub.add_parser("list", help="List registered proxies")
    p_list.add_argument("--server", default=API_HOST_DEFAULT, help="curllm API host")
    p_list.set_defaults(func=cmd_list)

    p_spawn = sub.add_parser("spawn", help="Spawn proxies on remote host via SSH using proxy.py")
    p_spawn.add_argument("--host", required=True, help="SSH target, e.g. user@host")
    p_spawn.add_argument("--ports", required=True, help="Comma-separated ports, e.g. 3128,3129")
    p_spawn.add_argument("--python", help="Remote python interpreter (default: python3)")
    p_spawn.add_argument("--ssh", help="SSH command (default: ssh)")
    p_spawn.add_argument("--server", default=API_HOST_DEFAULT, help="curllm API host")
    p_spawn.set_defaults(func=cmd_spawn)

    return p


def main(argv: List[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
