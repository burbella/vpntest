#-----provides DNS services-----
# no Config or DB modules loaded here, only BIND/DNS services
# Config module loads this module, so we don't want this module to load Config

#TODO:
# query() is deprecated, replace with resolve()

import dns.rdatatype
import dns.resolver
import dns.reversename
import socket
from functools import lru_cache

# This module cannot import the full zzzevpn because it would cause import loops
# import zzzevpn.IPutil
import zzzevpn

class DNSservice:
    'DNS services'
    
    default_resolver = None
    google_my_ip_server = 'o-o.myaddr.l.google.com'
    google_ns1 = 'ns1.google.com'
    ip_util = None
    
    def __init__(self):
        self.default_resolver = dns.resolver.Resolver()
        self.ip_util = zzzevpn.IPutil()
    
    #--------------------------------------------------------------------------------
    
    def lookup_ipv4_by_socket(self, host, retry=0):
        ip = ''
        try:
            ip = socket.gethostbyname(host)
        except:
            #TODO: log the error?
            return ''
        return ip
    
    #-----lookup the IPv4 of a given host-----
    # return answers[0].strings[0].decode("utf-8")
    def lookup_ipv4(self, host, retry=0):
        answers = ''
        try:
            # answers = self.default_resolver.query(host, 'A')
            answers = self.default_resolver.resolve(qname=host, rdtype=dns.rdatatype.RdataType.A, search=True)
        except:
            #TODO: log the error?
            return ''
        if not answers:
            return ''
        result = answers[0]
        if not result:
            return ''
        result_str = result.strings[0]
        if not result_str:
            return ''
        return result_str.decode("utf-8")
    
    #-----lookup the IPv6 of a given host-----
    # return answers[0].address
    def lookup_ipv6(self, host, retry=0):
        answers = ''
        try:
            # answers = self.default_resolver.query(host, 'AAAA')
            answers = self.default_resolver.resolve(qname=host, rdtype=dns.rdatatype.RdataType.AAAA, search=True)
        except:
            #TODO: log the error?
            return ''
        if not answers:
            return ''
        result = answers[0]
        if not result:
            return ''
        ip = result.address
        if not ip:
            return ''
        return ip
    
    #--------------------------------------------------------------------------------
    
    #-----the supplied nameserver IP will determine if IPv4 or IPv6 is returned-----
    def _lookup_external_ip(self, ns, retry: int=0):
        if retry < 0:
            retry = 0
        resolver = dns.resolver.Resolver(configure=False)
        # custom nameserver for this lookup
        resolver.nameservers = [ns]
        answers = None
        try:
            # answers = resolver.query(self.google_my_ip_server, 'TXT')
            answers = resolver.resolve(qname=self.google_my_ip_server, rdtype=dns.rdatatype.RdataType.TXT, search=True)
        except:
            return None
        if not answers:
            return None
        return answers[0].strings[0].decode("utf-8")
    
    #-----lookup external IPv4-----
    # command-line version:
    # dig -4 TXT +short o-o.myaddr.l.google.com @ns1.google.com | tr -d '"'
    @lru_cache(maxsize=2)
    def lookup_my_external_ipv4(self, retry: int=0):
        #-----need an IPv4 for google DNS-----
        ns = None
        try:
            ns = socket.gethostbyname(self.google_ns1)
        except:
            return None
        #-----ask google what is our external IPv4-----
        return self._lookup_external_ip(ns, retry)
    
    #-----lookup external IPv6-----
    # command-line version:
    # dig -6 TXT +short o-o.myaddr.l.google.com @ns1.google.com | tr -d '"'
    @lru_cache(maxsize=2)
    def lookup_my_external_ipv6(self, retry: int=0):
        #-----need an IPv6 for google DNS-----
        ns = None
        try:
            ns = self.lookup_ipv6(self.google_ns1)
        except:
            return None
        #-----ask google what is our external IPv6-----
        return self._lookup_external_ip(ns)
    
    #--------------------------------------------------------------------------------
    
    #TODO: factor-in DNS server performance limits, sleep as needed
    #-----big cache is more useful for large squid log processing-----
    @lru_cache(maxsize=2000)
    def lookup_reverse_dns_cached(self, ip):
        return self.lookup_reverse_dns(ip)
    
    def lookup_reverse_dns(self, ip) -> str:
        if not ip:
            return 'ERROR: not an IP'
        if not self.ip_util.is_ip(ip):
            return 'ERROR: not an IP'
        if not self.ip_util.is_public_ip(ip):
            return 'PRIVATE IP'
        
        reversed_address = ''
        try:
            reversed_address = dns.reversename.from_address(ip)
        except:
            return ip
        if not reversed_address:
            print('ERROR: dns.reversename.from_address() failed for ' + ip)
            return ip
        
        answers = ['']
        try:
            # answers = self.default_resolver.query(reversed_address, 'PTR')
            answers = self.default_resolver.resolve(qname=reversed_address, rdtype=dns.rdatatype.RdataType.PTR, search=True)
        except dns.resolver.NXDOMAIN as e:
            #-----common, not a serious error, don't log it-----
            #print('lookup_reverse_dns - resolver.query() found no reverse DNS entry for ' + ip)
            return ip
        except dns.exception.DNSException as e:
            print('lookup_reverse_dns - resolver.resolve() - other DNS error for ' + ip)
            print('     ' + str(e))
            return ip
        except:
            return ip
        
        if answers[0]:
            return str(answers[0])
        else:
            print('ERROR: lookup_reverse_dns - answers[0] is empty for ' + ip)
            return ip
    
    #--------------------------------------------------------------------------------
