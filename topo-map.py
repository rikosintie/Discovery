#!/usr/bin/env python3
"""
topo-map.py - draws a network topology diagram from every CDP/LLDP capture
config-pull.py has collected, as Graphviz SVG and PNG.

Reads every Interface/*-cdp.txt and Interface/*-lldp.txt - both protocols,
every host, since a topology view needs the whole network, not one switch -
and reuses ne_common.py's per-record tidying (interface shortening,
vendor-prefix stripping, MAC-only-neighbor vendor lookup) instead of
re-deriving any of it. cdp-ne.py/lldp-ne.py stay single-host table reports;
this is the whole-network graph view built on the same normalized data.

Each neighbor sighting becomes one edge between two nodes: the local switch
(from the capture's filename) and whatever it saw on that port. The same
physical device merges into one node wherever it's seen - "jc-mdf-4" (a
capture host) and "JC-MDF-4.tricommanagement.local" (how jc-core's CDP
capture names it as a neighbor) fold together case-insensitively. A link
reported from both ends, or by both CDP and LLDP, collapses to one edge
instead of drawing it twice.

Node roles
----------
Every capture host is a switch by definition - config-pull.py only runs
against managed switches - so local hosts are always "core". Anything that
only ever shows up as a *neighbor* is classified from its advertised
capabilities:

  * phone  - CDP "Phone", LLDP "T" / "telephone"          (checked first)
  * core   - CDP "Router"/"Switch", LLDP "R"/"B"/"router"/
             "bridge"/"wlan-access-point"                  (switches, routers, APs)
  * other  - anything else (PCs, printers, unclassified devices)

This is token-based, not an exact capability-string match: a plain access
switch that only ever advertises "Switch IGMP" (no "Router") still counts as
core - a literal "Router Switch IGMP" match would have missed it.

Filtering
---------
    -s, --core     keep only core-to-core links (switches/routers/APs)
    -p, --phones   keep only phones - and, since a phone's only possible
                   neighbor is a switch, each phone's own switch too, even
                   without -s
    -s -p together keep core-to-core links AND phones - an edge switch's
                   uplink to the core and its phones/APs both survive, which
                   is the common shape worth diagramming
    (neither)      the whole topology, unfiltered

An edge survives the filter only if both its endpoints do (the -p exception
above aside); a node left with no edges afterward is dropped rather than
drawn floating.

Link speed
----------
Looked up from the LOCAL host's own <host>-interface.json (Cisco only - HP
ProCurve's -interface.json has no speed field, only port counters) and
attached to whichever end of the edge can supply it.

Usage
-----
    python3 topo-map.py                  # everything
    python3 topo-map.py -s               # core backbone only
    python3 topo-map.py -p               # phones only
    python3 topo-map.py -s -p            # core + phones (edge-switch view)
    python3 topo-map.py -o site1-topology
"""

import argparse
import json
import os
import re
import subprocess
import sys

import ne_common as nc

_PHONE_CDP_TOKENS = {"Phone"}
_CORE_CDP_TOKENS = {"Router", "Switch"}
_PHONE_LLDP_TOKENS = {"T", "telephone"}
_CORE_LLDP_TOKENS = {"R", "B", "router", "bridge", "wlan-access-point"}

_ROLE_STYLE = {
    "core": ("box", "#4c78a8"),
    "phone": ("ellipse", "#59a14f"),
    "other": ("box", "#bab0ac"),
}
_ROLE_RANK = {"other": 0, "core": 1, "phone": 2}


def classify_cdp(caps: str) -> str:
    """CDP capabilities string -> "phone" | "core" | "other"."""
    tokens = set((caps or "").split())
    if tokens & _PHONE_CDP_TOKENS:
        return "phone"
    if tokens & _CORE_CDP_TOKENS:
        return "core"
    return "other"


def classify_lldp(caps: str) -> str:
    """LLDP capabilities (letter flags "B,T" or words "bridge, router") -> role."""
    tokens = {part.strip() for part in (caps or "").split(",") if part.strip()}
    if tokens & _PHONE_LLDP_TOKENS:
        return "phone"
    if tokens & _CORE_LLDP_TOKENS:
        return "core"
    return "other"


def canonical_key(raw: str) -> str:
    """Case/notation-insensitive identity for dedup across every capture.

    Mirrors ne_common.tidy_name()'s FQDN-trim heuristic but returns a stable
    key instead of a display string: two differently-cased sightings of the
    same hostname, or a bare vs. domain-qualified name, must fold to one
    node. A MAC-only chassis id is normalized (no vendor lookup) so two
    different unnamed devices that merely share an OUI stay separate nodes.
    """
    text = (raw or "").strip()
    if nc.is_mac(text):
        return re.sub(r"[.:\- ]", "", text).lower()
    text = nc.strip_vendor_prefix(text)
    if " " not in text and "." in text and not text.replace(".", "").isdigit():
        text = text.split(".")[0]
    return text.lower()


def read_interface_speeds(host: str) -> dict[str, str]:
    """interface -> speed ("1000Mb/s") from <host>-interface.json.

    Empty for a missing file, or a vendor whose capture has no speed field
    (HP ProCurve only reports port counters).
    """
    path = os.path.join("Interface", f"{host}-interface.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    if not isinstance(data, list):
        return {}
    return {
        rec["interface"]: rec["speed"]
        for rec in data
        if isinstance(rec, dict) and rec.get("interface") and rec.get("speed")
    }


class Node:
    __slots__ = ("key", "label", "role", "is_host")

    def __init__(self, key: str, label: str, role: str, is_host: bool):
        self.key = key
        self.label = label
        self.role = role
        self.is_host = is_host


def build_graph() -> tuple[dict[str, Node], dict[frozenset, dict]]:
    """Scan every CDP/LLDP capture and return (nodes, edges), deduped."""
    nodes: dict[str, Node] = {}
    edges: dict[frozenset, dict] = {}
    speed_cache: dict[str, dict[str, str]] = {}

    def upsert_node(key: str, label: str, role: str, is_host: bool) -> None:
        existing = nodes.get(key)
        if existing is None:
            nodes[key] = Node(key, label, role, is_host)
            return
        if is_host:
            # A capture host is always a switch, no matter how a neighbor's
            # sighting of it (processed in either order) classified it.
            existing.role = "core"
            existing.is_host = True
            existing.label = label
        else:
            if _ROLE_RANK[role] > _ROLE_RANK[existing.role]:
                existing.role = role
            # Prefer a name the device actually advertised over an
            # OUI-guessed one, whichever sighting arrived first.
            if "(unnamed)" in existing.label and "(unnamed)" not in label:
                existing.label = label

    for kind, classify in (("cdp", classify_cdp), ("lldp", classify_lldp)):
        for path in nc.discover_captures(kind):
            host = nc.host_from_capture(path, kind)
            host_key = canonical_key(host)
            upsert_node(host_key, host, "core", is_host=True)

            records = nc.load_records(path)
            if not records:
                continue
            if host_key not in speed_cache:
                speed_cache[host_key] = read_interface_speeds(host)
            speeds = speed_cache[host_key]

            for rec in records:
                raw_name = (rec.get("neighbor_name") or rec.get("chassis_id") or "").strip()
                if not raw_name:
                    continue
                neighbor_key = canonical_key(raw_name)
                if neighbor_key == host_key:
                    continue  # a device reporting itself - capture artifact
                role = classify(rec.get("capabilities", ""))
                upsert_node(neighbor_key, nc.tidy_name(raw_name), role, is_host=False)

                local_if = nc.shorten_interface(rec.get("local_interface", ""))
                if kind == "cdp":
                    remote_if = nc.shorten_interface(rec.get("neighbor_interface", ""))
                else:
                    remote_if = nc.shorten_interface(
                        rec.get("neighbor_port_id") or rec.get("neighbor_interface") or ""
                    )

                edge_key = frozenset({(host_key, local_if), (neighbor_key, remote_if)})
                speed = speeds.get(rec.get("local_interface", ""), "")
                edge = edges.get(edge_key)
                if edge is None:
                    edges[edge_key] = {
                        "a": host_key,
                        "a_if": local_if,
                        "b": neighbor_key,
                        "b_if": remote_if,
                        "speed": speed,
                    }
                elif speed and not edge["speed"]:
                    edge["speed"] = speed

    return nodes, edges


def filter_graph(
    nodes: dict[str, Node], edges: dict[frozenset, dict], roles: set[str] | None
) -> tuple[dict[str, Node], list[dict]]:
    """Apply the role filter, then drop nodes that end up with no edges.

    `roles=None` means no filter was requested - keep everything. Otherwise
    an edge normally survives only if both endpoints' roles are in `roles`.
    The one exception: a phone's only possible neighbor is a switch (always
    "core"), so requiring both ends to satisfy the filter would make -p
    alone always empty. When "phone" is requested, an edge touching a phone
    survives regardless of the other end's role, pulling in each phone's
    switch even without -s. -s alone is unaffected - it still keeps only
    core-to-core edges, not every switch's leaves.
    """
    if roles is None:
        return dict(nodes), list(edges.values())

    def edge_survives(edge: dict) -> bool:
        a_role, b_role = nodes[edge["a"]].role, nodes[edge["b"]].role
        if a_role in roles and b_role in roles:
            return True
        return "phone" in roles and (a_role == "phone" or b_role == "phone")

    kept_edges = [edge for edge in edges.values() if edge_survives(edge)]
    connected = {edge["a"] for edge in kept_edges} | {edge["b"] for edge in kept_edges}
    kept_nodes = {key: node for key, node in nodes.items() if key in connected}
    return kept_nodes, kept_edges


def _dot_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def to_dot(nodes: dict[str, Node], edges: list[dict]) -> str:
    """Render the filtered graph as Graphviz DOT source."""
    lines = [
        "graph topology {",
        "  rankdir=LR;",
        "  node [fontname=Helvetica, fontsize=10, style=filled, fontcolor=white];",
        "  edge [fontname=Helvetica, fontsize=9];",
    ]
    for node in nodes.values():
        shape, color = _ROLE_STYLE[node.role]
        lines.append(
            f'  "{node.key}" [label="{_dot_escape(node.label)}", '
            f'shape={shape}, fillcolor="{color}"];'
        )
    for edge in edges:
        # Escape each piece before joining with DOT's own "\n" line-break
        # escape - escaping the finished string would double up that
        # backslash and print a literal "\n" instead of breaking the line.
        label = _dot_escape(f"{edge['a_if']} - {edge['b_if']}")
        if edge["speed"]:
            label += "\\n" + _dot_escape(edge["speed"])
        lines.append(f'  "{edge["a"]}" -- "{edge["b"]}" [label="{label}"];')
    lines.append("}")
    return "\n".join(lines)


def render(dot_source: str, out_base: str) -> None:
    """Write <out_base>.dot and shell out to `dot` for .svg and .png."""
    dot_path = f"{out_base}.dot"
    with open(dot_path, "w", encoding="utf-8") as handle:
        handle.write(dot_source)
    print(f"Wrote {dot_path}")
    for fmt in ("svg", "png"):
        out_path = f"{out_base}.{fmt}"
        try:
            subprocess.run(["dot", f"-T{fmt}", dot_path, "-o", out_path], check=True)
            print(f"Wrote {out_path}")
        except FileNotFoundError:
            print("Graphviz's `dot` command was not found - install graphviz to render images.")
            sys.exit(1)
        except subprocess.CalledProcessError as exc:
            print(f"dot failed rendering {fmt}: {exc}")
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Draw a network topology diagram from every CDP/LLDP capture."
    )
    parser.add_argument(
        "-s",
        "--core",
        action="store_true",
        help="keep only core-to-core links (switches/routers/APs)",
    )
    parser.add_argument(
        "-p",
        "--phones",
        action="store_true",
        help="keep only phones, plus each phone's own switch",
    )
    parser.add_argument(
        "-o",
        "--out",
        default="topology",
        help='output basename - writes <out>.dot/.svg/.png (default: "topology")',
    )
    args = parser.parse_args()

    nodes, edges = build_graph()
    if not nodes:
        print("No CDP/LLDP captures found in Interface/.")
        sys.exit(1)

    roles: set[str] | None = None
    if args.core or args.phones:
        roles = set()
        if args.core:
            roles.add("core")
        if args.phones:
            roles.add("phone")

    kept_nodes, kept_edges = filter_graph(nodes, edges, roles)
    if not kept_edges:
        print("Nothing left after filtering - no edges match the requested role(s).")
        sys.exit(1)

    print(f"{len(kept_nodes)} device(s), {len(kept_edges)} link(s)")
    render(to_dot(kept_nodes, kept_edges), args.out)


if __name__ == "__main__":
    main()
