#coding=utf-8
"""kube2pyconsul.

Usage:
  kube2pyconsul.py [-v <loglevel>] [--verify-ssl=<value>] [--consul-agent=<consul-uri>] [--kube-master=<kubeapi-uri>] [--consul-auth=<user,pass>] [--kube-auth=<user,pass>]
  kube2pyconsul.py (-h | --help)

Options:
  -h --help     Show this screen.
  -v <loglevel>           Set logging level [default: INFO]
  --consul-agent=<consul-uri>  Consul agent location [default: https://127.0.0.1:8500].
  --kube-master=<kubeapi-uri>  Kubeapi location [default: https://127.0.0.1:6443]
  --consul-auth=<user,pass>    Consul http auth credentials [default: None]
  --kube-auth=<user,pass>      Kubernetes http auth credentials [default: None]
  --verify-ssl=<value>         Option to enable or disable SSL certificate validation [default: False]

"""
from docopt import docopt

import sys
import json
import time
import logging
import requests
import traceback
import multiprocessing

import socket
import struct
import fcntl
import os

from multiprocessing import Queue
from multiprocessing import Process

args = docopt(__doc__, version='kube2pyconsul 1.0')

logging.basicConfig()
log = multiprocessing.log_to_stderr()
level = logging.getLevelName(args['-v'])
log.setLevel(level)


consul_uri = args['--consul-agent']
consul_auth = tuple(args['--consul-auth'].split(',')) if args['--consul-auth'] != 'None' else None

kubeapi_uri = args['--kube-master']
kube_auth = tuple(args['--kube-auth'].split(',')) if args['--kube-auth'] != 'None' else None

verify_ssl = args['--verify-ssl']


log.info("Starting with: consul={0}, kubeapi={1}".format(consul_uri, kubeapi_uri))

def is_num_by_except(num):
    try:
        int(num)
        return True
    except ValueError:
        return False

def getip(ethname):

        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
                return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0X8915, struct.pack('256s', ethname[:15]))[20:24])
        except Exception as e:
                return getip('br0')



def getservice(event, ports):
    return {"Name": event['object']['metadata']['labels']['name'], 
            "ID": '{}'.format(event['object']['metadata']['name'] + '-' + str(ports)),
            "Address": event['object']['status']['podIP'], 
	    "port": ports}
            
    
def pods_monitor(queue):
    while True:
        try:
            r = requests.get('{base}/api/v1/pods?watch=true'.format(base=kubeapi_uri), 
                                 stream=True, verify=verify_ssl, auth=kube_auth)
            for line in r.iter_lines():
                if line:
                    event = json.loads(line)
                    
                    queue.put(('pod', event))
        except Exception as e:
          log.debug(traceback.format_exc())
          log.error(e)
          log.error("Sleeping and restarting afresh.")
          time.sleep(10)


def registration(queue):
    while True:
        context, event = queue.get(block=True)
        
        if context == 'pod':
	    '''
	    ifconfig 取得结果是物理机的ip，ip r取得docker化的ip，因为docker化之后ifconfig格式变了 
            iplist = os.popen("ifconfig |grep broadcast|grep -Ev ' 192| 172| 127'|awk '{print $2}'|xargs").read().strip().split(' ')
	    '''
	    iplist = os.popen("ip r|awk '{print $5}'|grep -Ev '192|172|eth'|xargs").read().strip().split(' ')
            if event['object']['spec']['nodeName'] in iplist:
                portlist = []
                for c in event['object']['spec']['containers']:
		    try:
			int(c['name'].split('-')[-1])
		    except Exception as e:
			pass
		    else:
 			portlist.append(c['name'].split('-')[-1])
                if event['type'] == 'ADDED':
                    #for ports in event['object']['metadata']['resourceVersion']:
		    portlist = map(int, portlist)
                    for ports in portlist:
                        service = getservice(event, ports)
                        r = ''
			#print service
			#print service['ID']
                        while True:
                            try:
                                r = requests.put('{base}/v1/agent/service/register'.format(base=consul_uri), 
                                                      json=service, auth=consul_auth, verify=verify_ssl)
                                break
                            except Exception as e:
                                log.debug(traceback.format_exc())
                                log.error(e)
                                log.error("Sleeping and retrying.")
                                time.sleep(10)
                                
                        if r.status_code == 200:
                            log.info("ADDED service {service} to Consul's catalog".format(service=service))
                        else:
                            log.error("Consul returned non-200 request status code. Could not register service {}. Continuing on to the next service...".format(service))
                        sys.stdout.flush()

                elif event['type'] == 'DELETED':
                    # for ports in event['object']['spec']['ports']:
                    for ports in portlist:
                        service = getservice(event, ports)
                        r = ''
                        
                        while True:
                            try:
                                r = requests.put('{base}/v1/agent/service/deregister/{name}'.format(base=consul_uri, name=service['ID']), 
                                                 auth=consul_auth, verify=verify_ssl)
                                break
                            except Exception as e:
                                log.debug(traceback.format_exc())
                                log.error(e)
                                log.error("Sleeping and retrying.")
                                time.sleep(10)
                                
                        if r.status_code == 200:
                            log.info("DELETED service {service} from Consul's catalog".format(service=service))
                        else:
                            log.error("Consul returned non-200 request status code. Could not deregister service {service}. Continuing on to the next service...".format())
                        sys.stdout.flush()
                      
        elif context == 'service':
            pass
        
        
def run():
    q = Queue()
    pods_watch = Process(target=pods_monitor, args=(q,), name='kube2pyconsul/pods')
    consul_desk = Process(target=registration, args=(q,), name='kube2pyconsul/registration')
    
    pods_watch.start()
    consul_desk.start()
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        pods_watch.terminate()
        consul_desk.terminate()
        
        exit()

if __name__ == '__main__':
    run()

