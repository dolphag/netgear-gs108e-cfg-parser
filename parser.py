#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
from pathlib import Path

LABELS = [
    b"qos",
    b"rate",
    b"storm",
    b"mirror",
    b"vlan",
    b"pvid",
    b"mcast",
    b"igmpsnoop",
    b"ethconfig",
    b"password",
    b"name",
    b"registration",
    b"loopdetect",
    b"misc",
    b"plusutility",
    b"plusutilitytftp",
    b"pwrSaving",
]


def find_sections(data: bytes) -> dict[str, bytes]:
    found = []
    for label in LABELS:
        pos = data.find(label)
        if pos >= 0:
            found.append((label.decode("ascii"), pos))
    found.sort(key=lambda x: x[1])

    sections: dict[str, bytes] = {}
    for i, (name, start) in enumerate(found):
        end = found[i + 1][1] if i + 1 < len(found) else len(data)
        sections[name] = data[start:end]
    return sections


def bitmask_to_ports(mask: int, width: int = 8) -> list[int]:
    return [i + 1 for i in range(width) if mask & (1 << i)]


def parse_name(payload: bytes) -> str | None:
    if not payload.startswith(b"name"):
        return None
    rest = payload[4:]
    if rest.startswith(b"\x00"):
        rest = rest[1:]
    s = []
    for c in rest:
        if c == 0:
            break
        if 32 <= c <= 126:
            s.append(chr(c))
        else:
            break
    return "".join(s) or None


def parse_ethconfig(payload: bytes) -> dict[str, str] | None:
    idx = payload.find(b"ethconfig")
    if idx < 0:
        return None
    rest = payload[idx + len(b"ethconfig") :]

    # observed format:
    # ethconfig 00 01 <ip4><mask4><gw4> ...
    for off in range(0, min(8, len(rest) - 14)):
        try:
            ip = str(ipaddress.IPv4Address(rest[off + 2 : off + 6]))
            mask = str(ipaddress.IPv4Address(rest[off + 6 : off + 10]))
            gw = str(ipaddress.IPv4Address(rest[off + 10 : off + 14]))
            if ip.startswith("172.") and gw.startswith("172."):
                return {"ip": ip, "netmask": mask, "gateway": gw}
        except Exception:
            pass
    return None


def parse_pvid(payload: bytes, ports: int = 8) -> list[int]:
    if not payload.startswith(b"pvid"):
        return []
    rest = payload[4:]
    vals = []
    for i in range(0, ports * 2, 2):
        vals.append(int.from_bytes(rest[i : i + 2], "big"))
    return vals


def parse_vlan_entries(payload: bytes) -> list[dict]:
    """
    Observed GS108Ev3 format:
      vlan
      00 04   # vlan count?
      00 04   # entry count?
      [VID:2][MEMBER:2][TAG:1] * n
    """
    if not payload.startswith(b"vlan"):
        return []

    rest = payload[4:]
    if len(rest) < 4:
        return []

    entry_count = int.from_bytes(rest[2:4], "big")
    pos = 4
    entries = []

    for _ in range(entry_count):
        if pos + 5 > len(rest):
            break
        vid = int.from_bytes(rest[pos : pos + 2], "big")
        member = int.from_bytes(rest[pos + 2 : pos + 4], "big")
        tag = rest[pos + 4]

        if not (1 <= vid <= 4094):
            break

        entries.append(
            {
                "vid": vid,
                "member_mask": member,
                "tag_mask": tag,
                "member_ports": bitmask_to_ports(member, width=16),
                "tagged_ports": bitmask_to_ports(tag, width=8),
            }
        )
        pos += 5

    for e in entries:
        member_set = set(e["member_ports"])
        tagged_set = set(e["tagged_ports"])
        e["untagged_ports"] = sorted(member_set - tagged_set)

    return entries


def render_markdown(file_path: Path) -> str:
    data = file_path.read_bytes()
    sections = find_sections(data)

    name = parse_name(sections.get("name", b"")) or file_path.stem
    eth = parse_ethconfig(sections.get("ethconfig", b"")) or {}
    pvids = parse_pvid(sections.get("pvid", b""))
    vlan_entries = parse_vlan_entries(sections.get("vlan", b""))

    lines = []
    lines.append(f"# {name}")
    lines.append("")

    lines.append("## Basic")
    if eth:
        lines.append(f"- Management IP: {eth.get('ip', '-')}")
        lines.append(f"- Netmask: {eth.get('netmask', '-')}")
        lines.append(f"- Gateway: {eth.get('gateway', '-')}")
    else:
        lines.append("- Management IP: unknown")
    lines.append("")

    lines.append("## PVID")
    lines.append("")
    lines.append("| Port | PVID |")
    lines.append("|---:|---:|")
    for i, v in enumerate(pvids, start=1):
        lines.append(f"| {i} | {v} |")
    lines.append("")

    lines.append("## VLAN table")
    lines.append("")
    lines.append("| VLAN | Member mask | Tag mask | Members | Tagged | Untagged |")
    lines.append("|---:|---:|---:|---|---|---|")
    for e in vlan_entries:
        members = ",".join(f"p{p}" for p in e["member_ports"]) or "-"
        tagged = ",".join(f"p{p}" for p in e["tagged_ports"]) or "-"
        untagged = ",".join(f"p{p}" for p in e["untagged_ports"]) or "-"
        lines.append(
            f"| {e['vid']} | 0x{e['member_mask']:04X} | 0x{e['tag_mask']:02X} | "
            f"{members} | {tagged} | {untagged} |"
        )
    lines.append("")

    lines.append("> 注: GS108Ev3 は複数VLANに非tagged参加しているように見えるポートが存在しうるため、")
    lines.append("> `untagged = member - tagged` をそのまま表示している。PVIDとは別概念として扱う。")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse GS108Ev3 cfg blob")
    parser.add_argument("file", type=Path, help="cfg-like file path")
    args = parser.parse_args()
    print(render_markdown(args.file))


if __name__ == "__main__":
    main()
