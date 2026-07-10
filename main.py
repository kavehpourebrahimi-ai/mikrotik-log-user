#!/usr/bin/env python3
"""MikroTik Log & Traffic Analyzer — CLI entry point."""

from __future__ import annotations

import argparse
import sys

from colorama import Fore, Style, init as colorama_init
from tabulate import tabulate

import config
from mikrotik_advanced import MikroTikConnection
from syslog_server import SyslogServer, log_store
from traffic_analyzer import analyze_user_traffic
from user_manager import get_user_info, list_all_users, search_by_group

colorama_init()


def print_header(title: str) -> None:
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


def menu_traffic_report(conn: MikroTikConnection) -> None:
    username = input("نام کاربر / Username: ").strip()
    logs = conn.fetch_logs(count=500, topics="hotspot")
    from log_parser import parse_log_line

    events = [parse_log_line(l) for l in logs]
    report = analyze_user_traffic(events, username)
    print_header(f"Traffic Report: {username or 'all'}")
    print(tabulate(report["source_ips"].items(), headers=["Source IP", "Count"]))
    print()
    print(tabulate(report["dest_ips"].items(), headers=["Dest IP", "Count"]))


def menu_users(conn: MikroTikConnection) -> None:
    users = list_all_users(host=conn.host)
    print_header("All Users")
    rows = [[u["name"], u["profile"], "Active" if not u["disabled"] else "Disabled"] for u in users]
    print(tabulate(rows, headers=["User", "Profile/Group", "Status"]))


def menu_export(conn: MikroTikConnection) -> None:
    logs = conn.fetch_logs(count=2000)
    for line in logs:
        log_store.add_raw(line, source=conn.host)
    path = log_store.save_snapshot()
    print(f"{Fore.GREEN}Exported {len(logs)} logs to {path}{Style.RESET_ALL}")


def run_cli() -> None:
    conn = MikroTikConnection()
    try:
        conn.connect()
        print(f"{Fore.GREEN}Connected to {conn.host}{Style.RESET_ALL}")
    except Exception as exc:
        print(f"{Fore.RED}Connection failed: {exc}{Style.RESET_ALL}")
        sys.exit(1)

    while True:
        print("\n" + Fore.YELLOW + "MikroTik Analyzer Menu" + Style.RESET_ALL)
        print("1. Traffic report")
        print("2. List users")
        print("3. Search by group")
        print("4. Export logs")
        print("5. Start web dashboard")
        print("0. Exit")
        choice = input("\nSelect: ").strip()

        if choice == "1":
            menu_traffic_report(conn)
        elif choice == "2":
            menu_users(conn)
        elif choice == "3":
            group = input("Group name: ").strip()
            users = search_by_group(group, host=conn.host)
            print(tabulate([[u["name"], u["profile"]] for u in users], headers=["User", "Group"]))
        elif choice == "4":
            menu_export(conn)
        elif choice == "5":
            conn.disconnect()
            from web_dashboard.app import run_dashboard

            print(f"\n{Fore.GREEN}Dashboard: http://{conn.host}:{config.WEB_PORT}{Style.RESET_ALL}")
            run_dashboard()
            return
        elif choice == "0":
            break

    conn.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="MikroTik Log & 4D Syslog Analyzer")
    parser.add_argument("--dashboard", action="store_true", help="Start web dashboard only")
    parser.add_argument("--syslog", action="store_true", help="Start syslog collector only")
    parser.add_argument("--host", default=None, help="MikroTik IP address")
    parser.add_argument("--port", type=int, default=None, help="Web dashboard port")
    args = parser.parse_args()

    if args.host:
        config.MIKROTIK_HOST = args.host

    if args.dashboard or args.syslog:
        server = SyslogServer(log_store)
        server.start()
        print(f"Syslog listening on UDP :{server.port}")
        if args.dashboard:
            from web_dashboard.app import run_dashboard

            run_dashboard(port=args.port)
        else:
            import time

            while True:
                time.sleep(60)
    else:
        run_cli()


if __name__ == "__main__":
    main()
