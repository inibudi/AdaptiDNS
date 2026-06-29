# nov/05/2025 09:08:15 by RouterOS 6.48.6
# software id = TH2N-4VIR
#
# model = RB941-2nD
# serial number = HCA07W3BM1H
/interface wireless
set [ find default-name=wlan1 ] disabled=no mode=ap-bridge ssid="DTE Unand"
/interface wireless security-profiles
set [ find default=yes ] supplicant-identity=MikroTik
/ip hotspot profile
add dns-name=login.sunaryo.id hotspot-address=10.5.50.1 name=hsprof1
/ip pool
add name=dhcp_pool1 ranges=192.168.1.2-192.168.1.254
add name=hs-pool-1 ranges=10.5.50.2-10.5.50.254
/ip dhcp-server
add address-pool=dhcp_pool1 disabled=no interface=ether2 name=dhcp1
add address-pool=hs-pool-1 disabled=no interface=wlan1 lease-time=1h name=\
    dhcp2
/ip hotspot
add address-pool=hs-pool-1 disabled=no interface=wlan1 name=hotspot1 profile=\
    hsprof1
/queue simple
add max-limit=10M/10M name=Queue-10M target=10.5.50.0/24
/ip neighbor discovery-settings
set discover-interface-list=!dynamic
/ip address
add address=192.168.1.1/24 interface=ether2 network=192.168.1.0
add address=10.5.50.1/24 interface=wlan1 network=10.5.50.0
/ip dhcp-client
add disabled=no interface=ether1
/ip dhcp-server network
add address=10.5.50.0/24 comment="hotspot network" dns-server=192.168.1.253 \
    gateway=10.5.50.1
add address=192.168.1.0/24 dns-server=192.168.1.253 gateway=192.168.1.1
/ip dns
set allow-remote-requests=yes servers=192.168.1.253
/ip firewall filter
add action=passthrough chain=unused-hs-chain comment=\
    "place hotspot rules here" disabled=yes
add action=accept chain=forward comment="Allow DNS UDP" dst-port=53 protocol=\
    udp
add action=accept chain=forward comment="Allow DNS TCP" dst-port=53 protocol=\
    tcp
add action=accept chain=input comment="API Access" dst-port=8728 protocol=tcp
/ip firewall nat
add action=masquerade chain=srcnat comment="Masquerade Internet" \
    out-interface=ether1
add action=masquerade chain=srcnat comment="Masquerade Hotspot" src-address=\
    10.5.50.0/24
add action=dst-nat chain=dstnat comment="DNS Redirect - Auth Users Only" \
    dst-port=53 hotspot=from-client,auth protocol=udp src-address=\
    10.5.50.0/24 to-addresses=192.168.1.253 to-ports=53
add action=dst-nat chain=dstnat comment="DNS Redirect TCP - Auth Users Only" \
    dst-port=53 hotspot=from-client,auth protocol=tcp src-address=\
    10.5.50.0/24 to-addresses=192.168.1.253 to-ports=53
add action=accept chain=dstnat comment="Exclude DNS Server" dst-address=\
    192.168.1.253 dst-port=53 protocol=udp
add action=accept chain=dstnat comment="Exclude DNS Server TCP" dst-address=\
    192.168.1.253 dst-port=53 protocol=tcp
add action=passthrough chain=unused-hs-chain comment=\
    "place hotspot rules here"
add action=redirect chain=dstnat disabled=yes dst-port=80 protocol=tcp \
    to-ports=8080
/ip hotspot ip-binding
add address=192.168.1.253 comment="Bypass Adminer server" type=bypassed
/ip hotspot user
add name=admin password=iniadmin
add name=budi password=inibudi
add name=sri password=inisri
add name=cinta password=inicinta
add name=lovely password=inilovely
/ip service
set api-ssl disabled=yes
/system clock
set time-zone-name=Asia/Jakarta
/system identity
set name=RouterOS
/system logging
add topics=hotspot
add topics=debug
