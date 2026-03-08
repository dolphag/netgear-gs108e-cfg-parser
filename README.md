# GS108Ev3 Config Parser

Unofficial Python parser for NETGEAR GS108Ev3 configuration backup blobs.

This project extracts a few practical fields from backup files, such as:

- device name
- management IPv4 settings
- PVID per port
- VLAN membership
- tagged / untagged port sets

It is intended for documentation, inventory, and migration work.

## Status

This is a reverse-engineered parser based on observed configuration blobs from real devices.

The format is **not officially documented** by NETGEAR.
The parser should be considered **best-effort** and may break on:

- different hardware revisions
- different firmware versions
- different switch models in the same family

## Features

- Parse section-based binary blobs
- Extract:
  - `name`
  - `ethconfig`
  - `pvid`
  - `vlan`
- Render human-readable Markdown output
- Help compare real switch state with inventory systems such as NetBox

## Example output

```text
# sw1

## Basic
- Management IP: 172.16.0.14
- Netmask: 255.255.254.0
- Gateway: 172.16.0.1

## PVID

| Port | PVID |
|---:|---:|
| 1 | 1 |
| 2 | 40 |
| 3 | 1 |
| 4 | 40 |
| 5 | 30 |
| 6 | 1 |
| 7 | 30 |
| 8 | 1 |
```
## Installation

Python 3.10+ is recommended.

```bash
git clone https://github.com/dolphag/gs108e-cfg-parser.git
cd gs108e-cfg-parser
python3 parser.py examples/sample.cfg
```

## Scope

This project focuses on a limited subset of the observed format:

* section discovery
* VLAN table parsing
* PVID parsing
* basic management IP parsing

It does **not** aim to provide full coverage of all possible fields.

## Safety and privacy

Do **not** publish real configuration backups from your own network.

Configuration backup files may contain sensitive information, including:

* real IP addresses
* hostnames
* VLAN design
* administrative metadata
* password-related fields

Only use sanitized or synthetic samples in public repositories.

## Binary format notes

The GS108E / GS108Ev3 backup file appears to be organized in labeled sections.

Known sections include:

- name
- ethconfig
- pvid
- vlan
- qos
- mirror
- storm
- igmpsnoop

The parser currently supports:

- device name
- management IPv4 settings
- PVID table
- VLAN membership table

### VLAN table format

The VLAN table appears to use the following structure:

vlan
[00 04]  VLAN count
[00 04]  entry count

Repeated entries:

[VID:2 bytes]
[MEMBER:2 bytes bitmap]
[TAG:1 byte bitmap]

Bit position corresponds to port number:

bit0 → port1
bit1 → port2
...
bit7 → port8

## Legal notice

This project is **unofficial** and is **not affiliated with, endorsed by, or supported by NETGEAR**.

The backup file format appears to be undocumented.
This repository contains only independently written parser code and does not include proprietary NETGEAR source code or firmware.

Before using or redistributing this tool, review the laws and license terms applicable in your jurisdiction and environment.

## Accuracy notice

This parser is based on observed samples and may contain mistakes.
Please verify the output against the switch GUI or other trusted sources before using it for production changes.

## Contributing

Bug reports and format notes are welcome.

If you submit sample data, please sanitize it first.

## License

MIT
