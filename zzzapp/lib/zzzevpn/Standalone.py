#-----standalone util class for storing constants and any common functions that do not require other zzzevpn modules-----
# util imports config and db
# this prevents config and db from using any functions in util
# functions not needing config or db should be moved to here

#-----package with all the Zzz modules-----
import zzzevpn

class Standalone:
    'standalone util class for storing constants and any common functions that do not require other zzzevpn modules'

    # boolean values
    BOOLEAN_STR_VALUES: list = ['TRUE', 'FALSE']

    # number constants
    MEGABYTE = 1024 * 1024
    GIGABYTE = 1024 * MEGABYTE

    #--------------------------------------------------------------------------------

    def __init__(self):
        self.init_vars()

    def init_vars(self):
        pass

    #--------------------------------------------------------------------------------

