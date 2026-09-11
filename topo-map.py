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

A phone (or any other leaf device) that CDP and LLDP name completely
differently - a Mitel phone is "SEP00085D65B42D" to CDP and "regDN
2281,MINET_6940" to LLDP, same handset - would otherwise show up as two
separate nodes hanging off the same switch port. When a switch port has
exactly one CDP neighbor and exactly one LLDP neighbor with different
names, they're merged into one node - the LLDP name is kept when both
exist, since it tends to carry the more useful information (extension/DN)
for phones in practice. This merge is deliberately narrow: a port with more
than one *real* LLDP neighbor - an IP phone with a PC daisy-chained into
its passthrough port shows up as two independent LLDP sightings on the same
switch port - is left as two separate nodes rather than guessed at.

A neighbor whose name field is just an identifier in disguise - a bare
chassis MAC, or an identifier restated with wrapper text ("Serial Number:
00104939517A" for a ShoreTel phone, matching the MAC already given
elsewhere in the same record; see ne_common.py's matching_identifier()) -
is labeled with its platform, then manufacturer, then an OUI-guessed vendor
as a last resort. The detector compares the digits themselves rather than
any vendor's wording, so an Avaya or Polycom doing the same "name is really
just an ID" trick is caught the same way, with no per-vendor phrase list.

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

Requires
--------
Graphviz's `dot` command on PATH - a system package, not a pip package, so
`pip install`/requirements.txt won't get it:

    Linux (Debian/Ubuntu): sudo apt install graphviz
    macOS (Homebrew):      brew install graphviz
    Windows (winget):      winget install --id Graphviz.Graphviz

See docs/Helper-scripts.md for the Windows/macOS notes (PATH, installer
fallback) that don't fit in a docstring.
"""

import argparse
import json
import os
import platform
import re
import subprocess
import sys

import ne_common as nc

_INSTALL_HINTS = {
    "Linux": "  Debian/Ubuntu: sudo apt install graphviz",
    "Darwin": "  macOS (Homebrew): brew install graphviz",
    "Windows": "  Windows (winget): winget install --id Graphviz.Graphviz\n"
    "  No winget? Download the installer from https://graphviz.org/download/",
}

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
    __slots__ = ("key", "label", "role", "is_host", "label_rank")

    def __init__(self, key: str, label: str, role: str, is_host: bool, label_rank: int = 0):
        self.key = key
        self.label = label
        self.role = role
        self.is_host = is_host
        self.label_rank = label_rank


# How much to trust a label when two sightings disagree on a leaf device's
# name: an OUI guess is a last resort; a platform string ("Cisco SG500X-24")
# beats that when the device sent one instead of a name; an actually
# advertised name beats either, and LLDP's tends to be more human-readable
# than CDP's MAC-derived device-id (Mitel's "SEP<mac>") for the same phone.
_LABEL_RANK = {"unnamed": 0, "platform": 1, "cdp": 2, "lldp": 3}


class _UnionFind:
    """Tracks which leaf-device sightings turned out to be the same node."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, key: str) -> str:
        self._parent.setdefault(key, key)
        while self._parent[key] != key:
            self._parent[key] = self._parent[self._parent[key]]
            key = self._parent[key]
        return key

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra


def build_graph() -> tuple[dict[str, Node], dict[object, dict]]:
    """Scan every CDP/LLDP capture and return (nodes, edges), deduped.

    Two passes: the first collects every sighting (a switch's own identity,
    and everything it sees on each port) without committing to node
    identity yet; the second resolves leaf devices that CDP and LLDP named
    differently but that showed up on the exact same switch port - almost
    certainly the same physical device - into one node before building the
    final edge list.
    """
    host_keys: set[str] = set()
    for kind in ("cdp", "lldp"):
        for path in nc.discover_captures(kind):
            host_keys.add(canonical_key(nc.host_from_capture(path, kind)))

    sightings: list[dict] = []
    port_neighbors: dict[tuple[str, str], dict[str, set[str]]] = {}
    speed_cache: dict[str, dict[str, str]] = {}

    for kind in ("cdp", "lldp"):
        classify = classify_cdp if kind == "cdp" else classify_lldp
        for path in nc.discover_captures(kind):
            host = nc.host_from_capture(path, kind)
            host_key = canonical_key(host)

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

                local_if = nc.shorten_interface(rec.get("local_interface", ""))
                if kind == "cdp":
                    remote_if = nc.shorten_interface(rec.get("neighbor_interface", ""))
                else:
                    remote_if = nc.shorten_interface(
                        rec.get("neighbor_port_id") or rec.get("neighbor_interface") or ""
                    )
                neighbor_platform = rec.get("platform", "")
                neighbor_manufacturer = rec.get("manufacturer", "")
                identifiers = (
                    rec.get("chassis_id", ""),
                    rec.get("neighbor_port_id", ""),
                    rec.get("mac_address", ""),
                )
                label = nc.tidy_name(
                    raw_name, neighbor_platform, neighbor_manufacturer, identifiers
                )
                # A name that's just a bare MAC, or an identifier restated
                # with wrapper text (a ShoreTel "Serial Number: <mac>"), is
                # not a real advertised name - rank it by whatever
                # resolve_unnamed() actually had to fall back to.
                is_fake_name = nc.is_mac(raw_name) or bool(
                    nc.matching_identifier(raw_name, identifiers)
                )
                if not is_fake_name:
                    label_rank = kind
                elif nc.strip_vendor_prefix(neighbor_platform) or nc.strip_vendor_prefix(
                    neighbor_manufacturer
                ):
                    label_rank = "platform"
                else:
                    label_rank = "unnamed"
                sightings.append(
                    {
                        "host_key": host_key,
                        "local_if": local_if,
                        "neighbor_key": neighbor_key,
                        "neighbor_is_host": neighbor_key in host_keys,
                        "label": label,
                        "label_rank": label_rank,
                        "role": classify(rec.get("capabilities", "")),
                        "remote_if": remote_if,
                        "speed": speeds.get(rec.get("local_interface", ""), ""),
                    }
                )
                if neighbor_key not in host_keys:
                    by_kind = port_neighbors.setdefault((host_key, local_if), {})
                    by_kind.setdefault(kind, set()).add(neighbor_key)

    # Same switch port, one CDP neighbor and one LLDP neighbor with different
    # names -> almost certainly one physical device (CDP and LLDP just
    # disagreeing on what to call it), so union them into one key. Only when
    # it's exactly one-and-one, though: a port can legitimately have more
    # than one *real* LLDP neighbor - an IP phone with a PC daisy-chained
    # into its passthrough port shows up as two separate LLDP sightings on
    # the same switch port, and those must stay two different nodes, not
    # merge into one.
    merges = _UnionFind()
    for by_kind in port_neighbors.values():
        cdp_keys, lldp_keys = by_kind.get("cdp", set()), by_kind.get("lldp", set())
        if len(cdp_keys) == 1 and len(lldp_keys) == 1:
            merges.union(next(iter(cdp_keys)), next(iter(lldp_keys)))

    nodes: dict[str, Node] = {}

    def upsert_node(key: str, label: str, role: str, is_host: bool, rank: int = 0) -> None:
        existing = nodes.get(key)
        if existing is None:
            nodes[key] = Node(key, label, role, is_host, rank)
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
            if rank >= existing.label_rank:
                existing.label = label
                existing.label_rank = rank

    for kind in ("cdp", "lldp"):
        for path in nc.discover_captures(kind):
            host = nc.host_from_capture(path, kind)
            upsert_node(canonical_key(host), host, "core", is_host=True)

    edges: dict[object, dict] = {}
    for sighting in sightings:
        neighbor_key = sighting["neighbor_key"]
        if not sighting["neighbor_is_host"]:
            neighbor_key = merges.find(neighbor_key)
        upsert_node(
            neighbor_key,
            sighting["label"],
            sighting["role"],
            is_host=False,
            rank=_LABEL_RANK[sighting["label_rank"]],
        )

        host_key, local_if = sighting["host_key"], sighting["local_if"]
        if sighting["neighbor_is_host"]:
            # Both switches may report this same link from their own end -
            # a symmetric key collapses either direction to one edge.
            edge_key = frozenset({(host_key, local_if), (neighbor_key, sighting["remote_if"])})
        else:
            # A leaf has no capture of its own to report the link back, so
            # identity is just "this switch port" once cross-protocol
            # sightings have already been merged into one neighbor_key above.
            edge_key = (host_key, local_if, neighbor_key)

        edge = edges.get(edge_key)
        if edge is None:
            edges[edge_key] = {
                "a": host_key,
                "a_if": local_if,
                "b": neighbor_key,
                "b_if": sighting["remote_if"],
                "speed": sighting["speed"],
            }
        else:
            if sighting["speed"] and not edge["speed"]:
                edge["speed"] = sighting["speed"]
            # Prefer a human-readable remote port ("Port 1") over a bare MAC
            # when CDP and LLDP disagree on how to describe the same port.
            if nc.is_mac(edge["b_if"]) and not nc.is_mac(sighting["remote_if"]):
                edge["b_if"] = sighting["remote_if"]

    return nodes, edges


def filter_graph(
    nodes: dict[str, Node], edges: dict[object, dict], roles: set[str] | None
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
            print(
                "Graphviz's `dot` command was not found on PATH - it's a system "
                "package, not something `pip install` can get you.\n"
                + _INSTALL_HINTS.get(platform.system(), _INSTALL_HINTS["Linux"])
                + "\nAlready installed? Open a new terminal - PATH changes made by "
                "an installer don't reach a session that was already running."
            )
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
