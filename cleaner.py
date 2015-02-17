#!/usr/bin/env python

"""cleaner.py  
checks and/or deletes - depending on excecution mode and existence -
B2FIND files on disc, datasets in CKAN database and/or 
and handles(PIDs) in EPIC handle server.

Copyright (c) 2014 Heinrich Widmann (DKRZ)

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Modified by  c/o DKRZ 2014   Heinrich Widmann
"""

import optparse, os, sys, re
import time
from epicclient import EpicClient,Credentials
from B2FIND import CKAN_CLIENT, UPLOADER, OUTPUT
import logging as log

def options_parser(modes):
    
    descI=""" 
   For each given entry existence checks and deletions of the following B2FIND objects is performed :                                           
              - 1. XML files on disc, harvested from OAI-PMH MD provider(s)\n\t
              - 2. JSON files on disc, generated by semantic mapping\n\t
              - 3. Uploaded CKAN datasets in the B2FIND catalogue and portal\n\t
              - 4. Handles (PIDs) in the EPIC handle server
"""
    p = optparse.OptionParser(
        description = "Description: checks and delete B2FIND files, datasets and handles from disk, CKAN database and EPIC handle server respectively.\n" + descI,
        formatter = optparse.TitledHelpFormatter(),
        prog = 'cleaner.py 0.1',
        epilog='For any further information and documentation please look at README.txt file or at the EUDAT wiki (-> JMD Software).',
        version = "%prog "
    )
   
        
    p.add_option('-v', '--verbose', action="count", 
                        help="increase output verbosity (e.g., -vv is more than -v)", default=False)
    p.add_option('-q', '--quiet', action="count", 
                        help="quiet modus : deletion is not really performed but only announced.", default=False)
    p.add_option('--jobdir', help='\ndirectory where log, error and html-result files are stored. By default directory is created as startday/starthour/processid .', default=None)
    p.add_option('--mode', '-m', metavar=' ' + " | ".join(modes), help='\nThis can be used to do a partial workflow. Default is "x-p" which means deletion of all found objects, i.e. (x)ml files, (j) json files, (c)kan datasets (p)id\'s in EPIC handle server.', default='x-p')
    p.add_option('--identifier', '-i', help="identifier for which objects are checked and deleted. If not given identifiers list must be given by -l option", default=None, metavar='STRING')
    p.add_option('--community', '-c', help="community for which objects are checked and deleted. If no value given identifiers from -i rsp. -l option is taken.", default=None, metavar='STRING')
    p.add_option('--fromdate', help="Filter harvested files by date (Format: YYYY-MM-DD).", default=None, metavar='DATE')
    p.add_option('--epic_check', 
         help="check and generate handles of CKAN datasets in handle server EPIC and with credentials as specified in given credstore file",
         default=None,metavar='FILE')
    p.add_option('--ckan_check',
         help="check existence and checksum against existing datasets in CKAN database",
         default='False', metavar='BOOLEAN')
    p.add_option('--outdir', '-d', help="The relative root dir in which all harvested files will be saved. The converting and the uploading processes work with the files from this dir. (default is 'oaidata')",default='oaidata', metavar='PATH')
    
         
    group_multi = optparse.OptionGroup(p, "Multi Mode Options",
        "Use these options if you want to ingest from a list in a file.")
    group_multi.add_option('--list', '-l', help="list of identifiers (-i mode) or communities sources (-c mode, default is ./harvest_list)", default=None,metavar='FILE')
    group_multi.add_option('--parallel', 
        help="[DEPRECATED]",#performs list of ingest requests in parallel (makes only sense with option [--list|-l] )",
        default='serial')     
    group_single = optparse.OptionGroup(p, "Single Mode Options",
        "Use these options if you want to ingest from only ONE source.")
    group_single.add_option('--source', '-s', help="A URL to .xml files which you want to harvest",default=None,metavar='PATH')
    group_single.add_option('--verb', help="Verbs or requests defined in OAI-PMH, can be ListRecords (default) or ListIdentifers here",default='ListRecords', metavar='STRING')
    group_single.add_option('--mdsubset', help="Subset of harvested meta data",default=None, metavar='STRING')
    group_single.add_option('--mdprefix', help="Prefix of harvested meta data",default=None, metavar='STRING')
    
    group_upload = optparse.OptionGroup(p, "Upload Options",
        "These options will be required to upload an dataset to a CKAN database.")
    group_upload.add_option('--host', help="host or IP adress of B2FIND portal (CKAN instance)", metavar='IP')
    group_upload.add_option('--auth', help="Authentification for CKAN APIs (API key, iby default taken from file $HOME/.netrc)",metavar='STRING')
    
    p.add_option_group(group_multi)
    p.add_option_group(group_single)
    p.add_option_group(group_upload)
    
    return p
    
    

def pstat_init (p,modes,mode,source,host):
    if (mode):
        if not(mode in modes):
           print("[ERROR] Mode " + mode + " is not supported")
           sys.exit(-1)
    else: # all processes (default)
        mode = 'h-u'
 
    # initialize status, count and timing of processes
    plist=['x','j','c','p']
    pstat = {
        'status' : {},
        'text' : {},
        'short' : [],
     }

    for proc in plist :
        pstat['status'][proc]='no'
        if ( proc in mode):
            pstat['status'][proc]='tbd'
        if (len(mode) == 3) and ( mode[1] == '-'): # multiple mode
            ind=plist.index(mode[0])
            last=plist.index(mode[2])
            while ( ind <= last ):
                pstat['status'][plist[ind]]='tbd'
                ind+=1
        
    if ( mode == 'c-p'):
        pstat['status']['a']='tbd'
        
    if source:
       stext='provider '+source
    else:
       stext='a list of MD providers'
       
    pstat['text']['x']='Delete XML files from disc '
    pstat['text']['j']='Delete JSON fieles from disc'  
    pstat['text']['c']='Delete datasets from CKAN server %s' % host
    pstat['text']['p']='Delete pids from EPIC handle server' 
    
    pstat['short'].append(['x', 'XML'])
    pstat['short'].append(['j', 'JSON'])
    pstat['short'].append(['c', 'CKAN'])
    pstat['short'].append(['p', 'PID'])
    
    return (mode, pstat)


def main():
    # parse command line options and arguments:
    modes=['x','xmlfiles','j','jsonfiles','c','ckandatasets','p','pids','x-p', 'x-j', 'j-c','j-p']
    p = options_parser(modes)
    options,arguments = p.parse_args()
    # check option 'mode' and generate process list:
    (mode, pstat) = pstat_init(p,modes,options.mode,options.source,options.host)

    # check for quiet mode
    if (options.quiet):
      qmsg='would be'
      mainmode='check'
    else:
      qmsg='is'   
      mainmode='deletion'

    if options.host :
       print "\tCKAN HOST:\t%s" % (options.host)
    if options.epic_check :
       print "\tCREDENTIAL:\t%s" % (options.epic_check)
    print '='*90

    # make jobdir
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    jid = os.getpid()
    print "\tStart of processing:\t%s" % (now)

    global logger
    OUT = OUTPUT(pstat,now,jid,options)
    logger = log.getLogger()

    # create credentials if required
    if (options.epic_check):
          try:
              credentials = Credentials('os',options.epic_check)
              credentials.parse()
          except Exception, err:
              logger.critical("[CRITICAL] %s Could not create credentials from credstore %s" % (err,options.epic_check))
              p.print_help()
              sys.exit(-1)
          else:
              logger.debug("Create EPIC client instance to add uuid to handle server")
              ec = EpicClient(credentials) 

 
    # checking given options:
    if (options.host):
        if (not options.auth):
             from os.path import expanduser
             home = expanduser("~")
             if(not os.path.isfile(home+'/.netrc')):
                logger.critical('[CRITICAL] Can not access job host authentification file %s/.netrc ' % home )
                exit()
             f = open(home+'/.netrc','r')
             lines=f.read().splitlines()
             f.close()

             l = 0
             for host in lines:
                if(options.host == host.split()[0]):
                   options.auth = host.split()[1]
                   break
        else:
            logger.critical(
                "\033[1m [CRITICAL] " +
                    "For CKAN database delete mode valid URL of CKAN instance (option --host) and API key (--auth or read from ~/.netrc) must be given" + "\033[0;0m"
            )
            sys.exit(-1)

        CKAN = CKAN_CLIENT(options.host,options.auth)
        UP = UPLOADER(CKAN, OUT)

    if (options.identifier):
             list = [ options.identifier ]
             listtext='given by option -i (%d id\'s)' % len(list) 
    elif (options.list):
             f = open(options.list,'r')
             list = f.readlines()
             f.close()
             listtext='got from file %s (%d id\'s)' % (options.list,len(list)) 
    elif (options.community):
             UP.get_packages(options.community)
             print "--- Start get community list from CKAN---\n"
             list = UP.package_list.keys()
             ##clist = UP.get_packages(options.community).keys()
             ##print clist
             listtext='got from CKAN community %s, stored in file %s-id.list  (%d id\'s)' % (options.community,options.community,len(list)) 
             cf = open('%s-id.list' % options.community,'w')
             cf.write("\n".join(list))
             cf.close()
             ##print UP.package_list.keys()
    else:
            print 'ERROR : one of the otptions -c COMMUNITY, -i IDENTIFIER or -l LIST must be given'
            sys.exit()

    ##HEW-Tprint '%s list ' % list
    ##HEW-Tsys.exit()

    
    print "\n=== Start %s processing ===\n\tTIME:\t%s\n\tID LIST:\t%s ... \n\t%s MODE:\t%s" % (mainmode,now,list[0:100], mainmode.upper(), options.mode)



    n=0
    xcount=0
    jcount=0
    ccount=0
    pcount=0
    print '\n| %-6s | %-50s | %-6s | %-6s | %-6s | %-6s |\n|%s|' % ('#', 'Identifier','XML','JSON','CKAN','EPIC',"-" * 53)
    for entry in list:
       n+=1
       dir = os.path.dirname(entry).rstrip()
       id, ext = os.path.splitext(os.path.basename(entry.rstrip()))
       id = id.split("_")[-1].lower()
       id = id.split()[-1]
       id = re.sub(r'^"|"$', '', id)
       actionreq=""
       actiontxt="Actions %s required : " % qmsg

       ### check,set and remove xml/json files
       xmlfile=None
       jsonfile=None
       xmlstatus=None
       jsonstatus=None
       xmlaction=''
       jsonaction=''

       if ( dir and ( ext == '.json' or ext == '.xml' ) ):
         ## print " FILES to remove :"  
         if ( ext == '.json' ):
           jsonfile='%s' % (entry.rstrip())
           xmlfile='%s/%s/%s%s' % (os.path.split(dir)[0],'xml',id,'.xml')
         elif ( ext == '.xml' ):
           xmlfile=entry.rstrip()
           jsonfile='%s/%s/%s%s' % (os.path.split(dir)[0],'json',id,'.json')

         if (os.path.isfile(xmlfile)):
             xmlstatus='exists'
             actionreq+=' remove xml file'
             if (not options.quiet):
               try:
                   os.remove(xmlfile)
               except Exception, e:
                 logger.error('[ERROR] Unexpected Error: %s' % e)
                 raise
               else:
                 ##print '\tXML file %s %s removed' % (xmlfile,qmsg)
                 xmlaction='removed'
         else:
             print "\tWARNING : Can not access %s for removing" % xmlfile
         if (os.path.isfile(jsonfile)):
             jsonstatus='exists'
             actionreq+=', remove json file'
             if (not options.quiet):
               try:
                 os.remove(jsonfile)
               except Exception, e:
                 logger.error('[ERROR] Unexpected Error: %s' % e)
                 raise
               else:
                 jsonaction='removed'
                 ##print '\tJSON file %s %s removed' % (jsonfile,qmsg)
         else:
             print "\tWARNING : Can not access %s for removing" % jsonfile
 ##      else:
 ##         print "  INFO : No directory or/and no supported extension %s given  => NO FILES to remove" % ext  

       # check and delete dataset and pid, if required
       ckanstatus=None
       epicstatus=None
       ckanaction=''
       epicaction=''

       if (options.epic_check or options.ckan_check=='True'):

         if (options.epic_check):
           # check against handle server EPIC
           epicstatus="unknown"
           pid = credentials.prefix + "/eudat-jmd_" + id.lower()
           checksum2 = ec.getValueFromHandle(pid,"CHECKSUM")
           b2findversion = ec.getValueFromHandle(pid,"JMDVERSION") 

           if (checksum2 == None):
             logger.debug("        |-> Can not access pid %s to get checksum" % (pid))
             epicstatus="new"
           else:
             logger.debug("        |-> pid %s exists" % (pid))
             print 'JMDVERSION %s' % b2findversion
             epicstatus="exist"
           ## print '\n EPIC status : %s' % epicstatus  
           if (epicstatus == 'exist'):
             actionreq+='\n\tPID %s%s%s %s removed' % (credentials.prefix,"/eudat-jmd_",id,qmsg)
             try:
               if (not options.quiet):
                 ec.deleteHandle(pid)
                 pcount+=1
                 epicaction='removed'
             except Exception, e:
               logger.error('[ERROR] Unexpected Error: %s' % e)
               epicaction='failed'
               raise

         ### check for and remove ckan dataset
         if (options.ckan_check == 'True'):
           # check for and remove ckan dataset
           ckanstatus = 'unknown'
           if (options.community):              
              checksum='fe5f25c9f6d17ba289d6551afc98a8c3'
              ckanstatus=UP.check_dataset(id,checksum)
           if (ckanstatus == 'unknown' or ckanstatus == 'changed' or ckanstatus == 'unchanged'):
             actionreq+=' remove ckan dataset'
             try:
               if (not options.quiet):
                 delete = UP.delete(id,ckanstatus)
                 if (delete == 1):
##                        logger.info('        |-> %s' % ('Deletion was successful'))
                        ccount +=  1
                        ckanaction='removed'
                 else:
                        ckanaction='failed'
             except Exception, e:
               logger.error('[ERROR] Unexpected Error: %s' % e)
               raise
       print '| %-6d | %-50s | %-6s | %-6s | %-6s | %-6s |' % (n, id,xmlstatus,jsonstatus,ckanstatus,epicstatus)
       if (not options.quiet):
         print '--> %-57s | %-6s | %-6s | %-6s | %-6s |' % ('action performed',xmlaction,jsonaction,ckanaction,epicaction)

    logger.info('end of cleaning ...')

if __name__ == "__main__":
    main()
