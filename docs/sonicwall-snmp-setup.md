# SonicWall TZ370 — SNMP Setup with Restricted Source Access

Firmware: SonicOS 7.0.1-5169

Goal: enable SNMP on the LAN (X0) interface, restricted to a single polling host
(`10.100.126.100`) on the `10.100.126.0/24` LAN zone.

## 1. Enable SNMP as a service

1. **Device | Settings | SNMP**
2. Check **Enable SNMP** → click **Accept**
3. Click **Configure** and set:
   - **Get Community Name** (used by `snmpwalk`/`snmpget` — this is your `-c` value)
   - Optionally **Trap Community Name** and **Host 1–n** if you want the firewall
     to send traps to a management system
4. Click **OK**

## 2. Enable SNMP on the LAN (X0) interface

1. **Network | System | Interfaces**
2. Edit **X0**
3. In the **Management** section, check **SNMP**
4. Click **OK**

This auto-generates a management access rule permitting SNMP to the firewall's
LAN IP — by default with **Source: Any**. That's the part locked down in step 4
below.

## 3. Create an address object for the polling host

1. **Object | Address Objects | Add**
2. Name: e.g. `snmp-poller`
3. Zone Assignment: **LAN**
4. Type: **Host**
5. IP Address: `10.100.126.100`
6. **Save**

## 4. Restrict the SNMP management rule's source

1. **Policy | Rules and Policies | Access Rules**
2. Switch view style to **Matrix**
3. Click the **LAN to LAN** cell
4. Find the auto-added SNMP management rule → **Configure**
5. Change **Source** from **Any** to `snmp-poller`
6. Click **OK**

This is the actual restriction — steps 1–3 just turn SNMP on. With Source scoped
to `snmp-poller`, only `10.100.126.100` can reach SNMP on the firewall; SonicOS
denies non-matching traffic on management rules by default, so nothing else on
the `/24` needs an explicit deny rule.

## 5. Test from the polling host

```bash
snmpwalk -v2c -c <community_string> 10.100.126.1 1.3.6.1.2.1.4.22
```

(OID `1.3.6.1.2.1.4.22` is the standard ARP MIB, `ipNetToMediaTable`.)

## Notes

- This sets up SNMP v1/v2c, which sends the community string in cleartext.
  SonicOS 7 also supports SNMPv3 with auth/priv if stronger security is needed
  — worth considering if the network carries anything sensitive, though v2c
  scoped to a single source IP is a reasonable tradeoff for a small site with
  limited security tooling.
- The same address-object + access-rule pattern applies to restricting other
  management services (HTTPS, SSH, ping) on any zone, not just SNMP on LAN.
