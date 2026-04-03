from typing import Dict, Optional
from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UsmUserData,
    UdpTransportTarget, ContextData, getCmd, nextCmd,
    ObjectType, ObjectIdentity,
    usmHMACMD5AuthProtocol, usmHMACSHAAuthProtocol,
    usmDESPrivProtocol, usmAesCfb128Protocol,
)
from pysnmp.proto.rfc1902 import OctetString


class SNMPScanner:
    """SNMP ARP table scanner."""

    def __init__(
        self,
        host: str,
        snmp_version: str = "v2c",
        community: Optional[str] = None,
        snmp_v3_config: Optional[dict] = None,
        timeout: int = 3,
        retry: int = 2,
    ):
        self.host = host
        self.snmp_version = snmp_version
        self.community = community or "public"
        self.snmp_v3_config = snmp_v3_config
        self.timeout = timeout
        self.retry = retry

    def _get_target(self) -> UdpTransportTarget:
        return UdpTransportTarget((self.host, 161), timeout=self.timeout, retries=self.retry)

    def _get_user_data(self):
        if self.snmp_version == "v3" and self.snmp_v3_config:
            cfg = self.snmp_v3_config
            auth_proto = usmHMACSHAAuthProtocol if cfg.get("auth_protocol") == "SHA" else usmHMACMD5AuthProtocol
            priv_proto = usmAesCfb128Protocol if cfg.get("priv_protocol") == "AES" else usmDESPrivProtocol
            return UsmUserData(
                cfg["username"],
                authKey=cfg["auth_password"],
                authProtocol=auth_proto,
                privKey=cfg["priv_password"],
                privProtocol=priv_proto,
            )
        return CommunityData(self.community, mpModel=1 if self.snmp_version == "v2c" else 0)

    def get_arp_table(self) -> Dict[str, str]:
        """Fetch ARP table from switch via SNMP."""
        result = {}

        # OID for IP-MIB::ipNetToMediaTable
        # .1.3.6.1.2.1.4.35.1.4 (ipNetToMediaPhysAddress)
        target = self._get_target()
        user_data = self._get_user_data()
        context = ContextData()

        try:
            iterator = nextCmd(
                SnmpEngine(),
                user_data,
                target,
                context,
                ObjectType(ObjectIdentity("1.3.6.1.2.1.4.35.1.4")),
                lexicographicMode=False,
            )

            for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                if errorIndication:
                    break
                if errorStatus:
                    break

                for varBind in varBinds:
                    ip_oid = str(varBind[0])
                    mac_raw = varBind[1]

                    # Extract IP from OID: .1.3.6.1.2.1.4.35.1.4.X.Y.Z.W => X.Y.Z.W
                    parts = ip_oid.rsplit(".", 4)
                    if len(parts) >= 4:
                        ip_str = ".".join(parts[-4:])

                    # MAC from OctetString
                    if isinstance(mac_raw, OctetString):
                        mac_bytes = mac_raw.asOctets()
                    else:
                        mac_bytes = bytes(mac_raw)

                    if len(mac_bytes) == 6:
                        mac_str = ":".join(f"{b:02X}" for b in mac_bytes)
                        result[ip_str] = mac_str

        except Exception:
            pass

        return result

    def test_connection(self) -> bool:
        """Test SNMP connectivity."""
        try:
            arp = self.get_arp_table()
            return True
        except Exception:
            return False
