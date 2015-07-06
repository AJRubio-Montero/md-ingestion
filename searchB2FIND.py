#!/usr/bin/env python

"""searchB2FIND.py  performs search request in the B2FIND metadata catalogue

Copyright (c) 2015 Heinrich Widmann (DKRZ)

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import os, sys
import argparse
import simplejson as json
import urllib, urllib2
from tables import *

def main():
    args = get_args()
    list = []
    
    print "\n%s" %('-'*100)
    # create CKAN search pattern :
    ckan_pattern = ''
    sand=''
    pattern=' '.join(args.pattern)
    ##pattern=args.pattern
    if (args.community):
        ckan_pattern += "groups:%s" % args.community
        sand=" AND "
    if (args.pattern):
        ckan_pattern += sand + pattern   

    print 'Search in\t%s\nfor pattern\t%s\n.....' % (args.ckan,ckan_pattern)
    ckan_limit=1000
    print 'processing %d to %d record ...' % (0,ckan_limit)
    answer = action(args.ckan, {"q":ckan_pattern,"rows":ckan_limit,"start":0})
    tcount=answer['result']['count']
    print "=> %d datasets found" % tcount
    print "=> %s args.output" % args.output
    ## print '    | %-4s | %-40s |\n    |%s|' % ('#','Dataset ID',"-" * 53)
    suppid={'id':'id','Source':'url','PID':'PID','DOI':'DOI'}

    class Record(IsDescription):
        id      = StringCol(64)      # 64-character String
        Source  = StringCol(64)      # 64-character String
        PID     = StringCol(64)      # 64-character String
        DOI     = StringCol(64)      # 64-character String

    h5file = open_file("results.h5", mode = "w", title = "Search results")
    group = h5file.create_group("/", 'identifiers', 'Identification information')
    table = h5file.create_table(group, 'readout', Record, "Readout example")
    record = table.row

    totlist=[]
    for outt in args.output:
       if outt in suppid :
          print 'Supported output type %s' % outt 
       else:
           print 'Output type %s is not supported' % outt
           exit()
    ##   fh=outt+'f' 
    ##   fh = open(outt+'list', 'w')      
    ##sf = open('source.file', 'w')
    ##pidf = open('pid.file', 'w')
    ##idf = open('id.file', 'w')
    countpid=0
    countdoi=0
    counter=0
    cstart=0

    while (cstart < tcount) :
       if (cstart > 0):
           print 'processing %d to %d record ...' % (cstart,cstart+ckan_limit)
           answer = action(args.ckan, {"q":ckan_pattern,"rows":ckan_limit,"start":cstart})
       for ds in answer['result']['results']:
            counter +=1
            ## print'    | %-4d | %-40s |' % (counter,ds['name'])

            record['id']  = '%s' % (ds['name'])
            record['Source']  = '%s' % (ds['url'])
            ##idf.write(ds['name']+'\n')
            ##sf.write(ds['url']+'\n')
            xpid=[e for e in ds['extras'] if e['key'] == 'PID']
            if xpid:
               ##print 'xpid %s' % xpid[0]['value']
               record['PID']  = '%s' % (xpid)
               countpid+=1
            else:
               ##print 'No PID available'
               record['PID']  = '%s' % 'N/A'
            xdoi=[e for e in ds['extras'] if e['key'] == 'DOI']
            if xdoi:
               ##print 'xdoi %s' % xdoi[0]['value']
               record['DOI']  = '%s' % (xdoi)
               countdoi+=1
            else:
               ##print 'No DOI available'
               record['DOI']  = '%s' % 'N/A'
            record.append()
       cstart+=len(answer['result']['results']) 

    print "Found\n\t%d\trecords\n\t%d\tPIDs\n\t%d\tDOIs" % (counter, countpid, countdoi)
    print "Results written to %s" % h5file.title
    table.flush()
    h5file.close()

def action(host, data={}):
    ## action (action, jsondata) - method
    # Call the api action <action> with the <jsondata> on the CKAN instance which was defined by iphost
    # parameter of CKAN_CLIENT.
    #
    # Parameters:
    # -----------
    # (string)  action  - Action name of the API v3 of CKAN
    # (dict)    data    - Dictionary with json data
    #
    # Return Values:
    # --------------
    # (dict)    response dictionary of CKAN
	    
    return __action_api(host,'package_search', data)
	
def __action_api (host,action, data_dict):
    # Make the HTTP request for data set generation.
    response=''
    rvalue = 0
    action_url = "http://{host}/api/3/action/{action}".format(host=host,action=action)

    # make json data in conformity with URL standards
    data_string = urllib.quote(json.dumps(data_dict))

    ##print('\t|-- Action %s\n\t|-- Calling %s\n\t|-- Object %s ' % (action,action_url,data_dict))	
    try:
       request = urllib2.Request(action_url)
       response = urllib2.urlopen(request,data_string)
    except urllib2.HTTPError as e:
       print '\t\tError code %s : The server %s couldn\'t fulfill the action %s.' % (e.code,host,action)
       if ( e.code == 403 ):
                print '\t\tAccess forbidden, maybe the API key is not valid?'
                exit(e.code)
       elif ( e.code == 409 and action == 'package_create'):
                print '\t\tMaybe the dataset already exists or you have a parameter error?'
                action('package_update',data_dict)
                return {"success" : False}
       elif ( e.code == 409):
                print '\t\tMaybe you have a parameter error?'
                return {"success" : False}
       elif ( e.code == 500):
                print '\t\tInternal server error'
                exit(e.code)
    except urllib2.URLError as e:
       exit('%s' % e.reason)
    else :
       out = json.loads(response.read())
       assert response.code >= 200
       return out

def get_args():
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description = "Description: Get PID's of datasets that fulfill the search criteria",
        epilog =  '''Examples:
           1. >./searchB2FIND.py -c aleph tags:LEP
             searchs for all datasets of community ALEPH with tag "LEP" in b2find.eudat.eu.
           2. >./searchB2FIND.py tags:PUBLICATIONOTHER author:'"Ahn, Changhyun"' --ckan eudat6c.dkrz.de
             searchs for all datasets tagged with PUBLICATIONOTHER and having author "Ahn, Changhyan" in eudat6c.dkrz.de''' 
    )
   
    p.add_argument('--ckan',  help='CKAN portal address, to which search requests are submitted (default is b2find.eudat.eu)', default='b2find.eudat.eu', metavar='IP/URL')
    p.add_argument('--community', '-c', help="Community where you want to search in", default='', metavar='STRING')
    p.add_argument('--output', '-o', help="Which identifiers should be outputed. Default is 'id'. Adiitioanl 'Source','PID' and 'DOI' are supported.", default=['id'], nargs='*')
    p.parse_args('--output'.split())
    p.add_argument('pattern',  help='CKAN search pattern, i.e. (a list of) field:value terms.', metavar='PATTERN', nargs='*')
    
    args = p.parse_args()
    
    if (not args.pattern) and (not args.community) :
        print "[ERROR] Need at least a community given via option -c or a search pattern as an argument!"
        exit()
    
    return args
               
if __name__ == "__main__":
    main()