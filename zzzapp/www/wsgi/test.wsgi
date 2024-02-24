#-----Settings page-----

import os

#WSGIScriptAlias /settings /var/www/wsgi/settings.wsgi

def make_data():
    data = 'TEST2 - WSGI Functionality'
    return data.encode('utf-8')

def application(environ, start_response):
    status = '200 OK'
    
    # output = b'TEST WSGI Functionality'
    output = make_data()
    
    #-----make HTML headers-----
    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

