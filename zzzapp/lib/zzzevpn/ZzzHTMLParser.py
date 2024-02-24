#-----Zzz Custom Extension of Python HTML Parser-----

from html.parser import HTMLParser
from html.entities import name2codepoint
import re

#-----import modules from the lib directory-----


class ZzzHTMLParser(HTMLParser):
    'Zzz Custom Extension of Python HTML Parser'
    
    # Initializing lists - test junk from an old reference?
    lsStartTags = []
    lsEndTags = []
    lsStartEndTags = []
    lsComments = []
    
    #-----collect all the items for analysis-----
    all_items = []
    num_items = 0
    
    #-----required items to prevent parser crashes-----
    cdata_elem = None
    convert_charrefs = None
    interesting = None # this is apparently a regex that takes '<' or '&'
    lineno = 0
    offset = 0
    rawdata = '' # this is not allowed to be None
    
    #--------------------------------------------------------------------------------
    
    def __init__(self):
        all_items = []
        num_items = 0
        
        #-----initialize the regex-----
        regex = r'<'
        self.interesting = re.compile(regex, re.IGNORECASE)
    
    #--------------------------------------------------------------------------------
    
    def inc_num_items(self):
        self.num_items += 1
    
    #--------------------------------------------------------------------------------
    
    #-----Required HTML Parser Methods-----
    def handle_starttag(self, tag, attrs):
        # print("Start tag:", tag)
        self.inc_num_items()
        self.all_items.append(['starttag', tag])
        for attr in attrs:
            # print("     attr:", attr)
            self.all_items.append(['attr', attr])
    
    def handle_endtag(self, tag):
        # print("End tag  :", tag)
        self.all_items.append(['endtag', tag])
    
    def handle_data(self, data):
        # print("Data     :", data)
        self.all_items.append(['data', data])
    
    def handle_comment(self, data):
        # print("Comment  :", data)
        self.all_items.append(['comment', data])
    
    def handle_entityref(self, name):
        c = chr(name2codepoint[name])
        # print("Named ent:", c)
        self.all_items.append(['named_ent', c])
    
    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        # print("Num ent  :", c)
        self.all_items.append(['num_ent', c])
    
    def handle_decl(self, data):
        # print("Decl     :", data)
        self.all_items.append(['decl', data])
    
    #--------------------------------------------------------------------------------
