#-----provides IP processing utilities-----
# IPv4 and IPv6
# no Config or DB modules loaded here, only IP services
# Config/DNSservice/Util modules load this module, so we don't want this module to load Config

import ipaddress

#-----import modules from the lib directory-----
# This module cannot import the full zzzevpn because it would cause import loops
# 6/12/2022: It should not import anything under zzzevpn

class IPutil:
    'IP utilities'
    
    ip = None
    net = None
    
    #-----details on various private subnets-----
    # calculated fields: ip4addr
    #
    # Reference:
    #   https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml
    #   https://en.wikipedia.org/wiki/Reserved_IP_addresses
    #
    # 0.0.0.0/8	0.0.0.0-0.255.255.255	16777216	Software	Current network[3] (only valid as source address).
    # 10.0.0.0/8	10.0.0.0-10.255.255.255	16777216	Private network	Used for local communications within a private network.[4]
    # 100.64.0.0/10	100.64.0.0-100.127.255.255	4194304	Private network	Shared address space[5] for communications between a service provider and its subscribers when using a carrier-grade NAT.
    # 127.0.0.0/8	127.0.0.0-127.255.255.255	16777216	Host	Used for loopback addresses to the local host.[3]
    # 169.254.0.0/16	169.254.0.0-169.254.255.255	65536	Subnet	Used for link-local addresses[6] between two hosts on a single link when no IP address is otherwise specified, such as would have normally been retrieved from a DHCP server.
    # 172.16.0.0/12	172.16.0.0-172.31.255.255	1048576	Private network	Used for local communications within a private network.[4]
    # 192.0.0.0/24	192.0.0.0-192.0.0.255	256	Private network	IETF Protocol Assignments.[3]
    # 192.0.2.0/24	192.0.2.0-192.0.2.255	256	Documentation	Assigned as TEST-NET-1, documentation and examples.[7]
    # 192.88.99.0/24	192.88.99.0-192.88.99.255	256	Internet	Reserved.[8] Formerly used for IPv6 to IPv4 relay[9] (included IPv6 address block 2002::/16).
    # 192.168.0.0/16	192.168.0.0-192.168.255.255	65536	Private network	Used for local communications within a private network.[4]
    # 198.18.0.0/15	198.18.0.0-198.19.255.255	131072	Private network	Used for benchmark testing of inter-network communications between two separate subnets.[10]
    # 198.51.100.0/24	198.51.100.0-198.51.100.255	256	Documentation	Assigned as TEST-NET-2, documentation and examples.[7]
    # 203.0.113.0/24	203.0.113.0-203.0.113.255	256	Documentation	Assigned as TEST-NET-3, documentation and examples.[7]
    # 224.0.0.0/4	224.0.0.0-239.255.255.255	268435456	Internet	In use for IP multicast.[11] (Former Class D network).
    # 240.0.0.0/4	240.0.0.0-255.255.255.254	268435455	Internet	Reserved for future use.[12] (Former Class E network).
    # 255.255.255.255/32	255.255.255.255	1	Subnet	Reserved for the "limited broadcast" destination address.[3][13]
    reserved_subnet_info = {
        'ipv4': {
            '0.0.0.0/8': {
                'description': 'Current network (only valid as source address)',
                'scope': 'N/A',
            },
            '10.0.0.0/8': {
                'description': 'Used for local communications within a private network',
                'scope': 'PRIVATE',
            },
            '100.64.0.0/10': {
                'description': 'Private network	Shared address space for communications between a service provider and its subscribers when using a carrier-grade NAT',
                'scope': 'CG-NAT',
            },
            '127.0.0.0/8': {
                'description': 'Used for loopback addresses to the local host',
                'scope': 'LOOPBACK',
            },
            '169.254.0.0/16': {
                'description': 'Used for link-local addresses between two hosts on a single link when no IP address is otherwise specified, such as would have normally been retrieved from a DHCP server',
                'scope': 'LINK-LOCAL',
            },
            '172.16.0.0/12': {
                'description': 'Used for local communications within a private network',
                'scope': 'PRIVATE',
            },
            '192.0.0.0/24': {
                'description': 'Private network	IETF Protocol Assignments',
                'scope': 'PRIVATE',
            },
            '192.0.2.0/24': {
                'description': 'TEST-NET-1, documentation and examples',
                'scope': 'Reserved',
            },
            '192.88.99.0/24': {
                'description': 'Reserved. Formerly used for IPv6 to IPv4 relay[9] (included IPv6 address block 2002::/16)',
                'scope': 'Reserved',
            },
            '192.168.0.0/16': {
                'description': 'Used for local communications within a private network',
                'scope': 'PRIVATE',
            },
            '198.18.0.0/15': {
                'description': 'Private network	Used for benchmark testing of inter-network communications between two separate subnets',
                'scope': 'PRIVATE',
            },
            '198.51.100.0/24': {
                'description': 'TEST-NET-2, documentation and examples',
                'scope': 'Reserved',
            },
            '203.0.113.0/24': {
                'description': 'TEST-NET-3, documentation and examples',
                'scope': 'Reserved',
            },
            '224.0.0.0/4': {
                'description': 'Multicast (Former Class D network)',
                'scope': 'MULTICAST',
            },
            '240.0.0.0/4': {
                'description': 'Reserved for future use (Former Class E network)',
                'scope': 'Reserved',
            },
        },
        'ipv6': {
        },
    }
    ipv4_reserved_subnets = reserved_subnet_info['ipv4'].keys()
    ipv4_cg_nat = None
    
    #-----subset of the ipv4_reserved_subnets-----
    # these are the only reserved subnets that tend to appear in normal traffic
    ipv4_private_subnets = [
        '10.0.0.0/8',
        '172.16.0.0/12',
        '192.168.0.0/16',
        '169.254.0.0/16',
        '100.64.0.0/10',
        '127.0.0.0/8',
    ]
    
    def __init__(self, ip_str=None):
        if ip_str:
            self.identify_str(ip_str)
        # prep the reserved subnets with ipaddress objects
        for subnet in self.ipv4_reserved_subnets:
            self.reserved_subnet_info['ipv4'][subnet]['IPv4Network'] = self.is_cidr(subnet)
        self.ipv4_cg_nat = self.is_cidr('100.64.0.0/10')
    
    #--------------------------------------------------------------------------------
    
    #-----check a given string to see what it is-----
    # IPv4 or IPv6?  OBJECT.version=4 or 6
    # IP address or Network?
    # ipaddress objects available: IPv4Address, IPv6Address, IPv4Network, IPv6Network
    def identify_str(self, ip_str):
        self.ip = None
        self.net = None
        if not ip_str:
            return False
        #-----check if we have a CIDR first-----
        self.net = self.is_cidr(ip_str)
        #-----no CIDR?  check if we have an IP-----
        if not self.net:
            self.ip = self.is_ip(ip_str)
    
    #--------------------------------------------------------------------------------
    
    #-----carrier-grade NAT seems to be a special category-----
    def is_cg_nat(self, ip=None, ip_obj=None):
        if ip:
            ip_obj = self.is_ip(ip)
        if ip_obj:
            result = ip_obj in self.ipv4_cg_nat
            return result
        return False
    
    #-----check if a given IP is reserved-----
    # default - rely on the python ipaddress.is_reserved flag
    # short list - more thorough than python is_reserved?
    # full list - includes test IP ranges that don't appear in normal traffic
    # returns: True/False and optional subnet key
    def is_reserved_ip(self, ip, short_list=False, full_list=False):
        result = {
            'is_reserved': False,
            'subnet': '', # key in the array reserved_subnet_info
        }
        
        ip_obj = self.is_ip(ip)
        if not ip_obj:
            return result
        
        if short_list:
            #TODO: replace with binary search tree
            for subnet in self.ipv4_private_subnets:
                if ip_obj in self.reserved_subnet_info['ipv4'][subnet]['IPv4Network']:
                    result['subnet'] = subnet
                    result['is_reserved'] = True
                    return result
        elif full_list:
            #TODO: replace with binary search tree
            for subnet in self.ipv4_reserved_subnets:
                if ip_obj in self.reserved_subnet_info['ipv4'][subnet]['IPv4Network']:
                    result['subnet'] = subnet
                    result['is_reserved'] = True
                    return result
        else:
            result['is_reserved'] = ip_obj.is_reserved
        
        return result
    
    def is_public_ip(self, ip):
        ip_obj = self.is_ip(ip)
        if ip_obj:
            return not ip_obj.is_private
        return False
    
    #-----check if it's an IP address-----
    def is_ip(self, host):
        try:
            ip_test = ipaddress.ip_address(host)
            return ip_test
        except ValueError:
            return None
    
    def is_cidr(self, cidr):
        try:
            cidr_test = ipaddress.ip_network(cidr, strict=False)
            return cidr_test
        except ValueError:
            return None
    
    #--------------------------------------------------------------------------------
    
    # lookup the description of the reserved subnet for an IP
    def lookup_reserved_subnet(self, ip, full_list=False):
        short_list = True
        if full_list:
            short_list = False
        result = self.is_reserved_ip(ip, short_list, full_list)
        if result['is_reserved']:
            return self.reserved_subnet_info['ipv4'][result['subnet']]['scope']
        return ''
    
    #--------------------------------------------------------------------------------
    
    #-----get the /64 for a given ipv6-----
    def calc_ipv6_64(self, server_ipv6):
        ipv6_64_net = ipaddress.IPv6Network(server_ipv6 + '/64', strict=False)
        ipv6_64 = str(ipv6_64_net)
        return ipv6_64
    
    #--------------------------------------------------------------------------------
