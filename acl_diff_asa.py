#!/usr/bin/env python 

import argparse
from difflib import unified_diff
from netmiko import ConnectHandler
import os
import subprocess
import sys

# Arguments
parser = argparse.ArgumentParser(description='Great Description To Be Here')

parser.add_argument('-i', type=str, dest='ip', help='ip address or fqdn')
parser.add_argument('-u', type=str, dest='login', help='login')
parser.add_argument('-p', type=str, dest='passw', help='password')
parser.add_argument('-s', type=str, dest='secret', help='secret')
parser.add_argument('-m', type=str, dest='mode', help='mode: single of multiple')
parser.add_argument('-z', type=str, dest='zabbix', help='zabbix: ip address of zabbix server')

res = parser.parse_args()
arg_ip = res.ip
arg_login = res.login
arg_passw = res.passw
arg_secret = res.secret
arg_mode = res.mode
arg_zabbix = res.zabbix

ASA5500 = {'device_type': 'cisco_asa','ip': arg_ip,'username': arg_login,'password': arg_passw, 'secret': arg_secret,}

conf1 = '/tmp/' + arg_ip + '/conf1'
conf2 = '/tmp/' + arg_ip + '/conf2'
diff = '/tmp/' + arg_ip + '/diff'
path = '/tmp/' + arg_ip

if os.path.isdir(path):
    pass
else:
    os.mkdir(path)

def single_mode():
    global conf1
    global conf2
    net_connect = ConnectHandler(**ASA5500)
    def getsingleconfig(arg1):
        arg1.write('\n' + '++++++++++++++++++++++++++ NAT ++++++++++++++++++++++++++' + '\n')
        outnat = net_connect.send_command('sh run nat')
        arg1.write(outnat)
        arg1.write('\n' + '+++++++++++++++++++++++++ GROUP +++++++++++++++++++++++++' + '\n')
        outgroup = net_connect.send_command('sh run access-group | include outside')
        arg1.write(outgroup)
        arg1.write('\n' + '++++++++++++++++++++++++++ ACL ++++++++++++++++++++++++++' + '\n') 
        gap = net_connect.send_command('sh access-list | include outside')
        strgap = str(gap)
        for aclline in strgap.splitlines():
            if not "remark" in aclline:
                fulllistgap = aclline.split(' ')
                listgap = fulllistgap[0:-3]
                acl = ' '.join(listgap)
                arg1.write(acl + '\n')
            else:
                arg1.write(aclline + '\n')
        arg1.close()
    
    if not os.path.exists(conf1):
        touch_conf = open(conf1, 'w').close()
        config1 = open(conf1,'a')
        getsingleconfig(config1)
        sys.exit(0)
    else:
        touch_conf = open(conf2, 'w').close()
        config2 = open(conf2,'a')
        getsingleconfig(config2)

    net_connect.disconnect()
	
def multiple_mode():
    global conf1
    global conf2
    net_connect = ConnectHandler(**ASA5500)
    all_commands = ['changeto system','show context detail | include Context']
    
    output = ''
    
    for command in all_commands:
        output += net_connect.send_command(command)
    
    stroutput = str(output)
    contexts = []
    for line in stroutput.splitlines():
        columns = line.split()
        if len(columns) > 0:
            contexts.append(columns[1][1:-2])
    
    del contexts[0]
    del contexts[-1]
    
    outconf = ''
    
    def getmultipleconfig(arg1):
        for i in contexts:
            changeto = str('changeto context ' + i)
            outconf = net_connect.send_command(changeto)
            arg1.write('\n' + '========================== ' + i + ' ==========================' + '\n')
            arg1.write('\n' + '++++++++++++++++++++++++++ NAT ++++++++++++++++++++++++++' + '\n')
            outnat = net_connect.send_command('sh run nat')
            arg1.write(outnat)
            arg1.write('\n' + '+++++++++++++++++++++++++ GROUP +++++++++++++++++++++++++' + '\n')
            outgroup = net_connect.send_command('sh run access-group | include outside')
            arg1.write(outgroup)
            arg1.write('\n' + '++++++++++++++++++++++++++ ACL ++++++++++++++++++++++++++' + '\n')
            gap = net_connect.send_command('sh access-list | include outside')
            strgap = str(gap)
            for aclline in strgap.splitlines():
                if not "remark" in aclline:
                    fulllistgap = aclline.split(' ')
                    listgap = fulllistgap[0:-3]
                    acl = ' '.join(listgap)
                    arg1.write(acl + '\n')
                else:
                    arg1.write(aclline + '\n')
        arg1.close()
    
    if not os.path.exists(conf1):
        touch_conf = open(conf1, 'w').close()
        config1 = open(conf1,'a')
        getmultipleconfig(config1)
        sys.exit(0)
    else:
        touch_conf = open(conf2, 'w').close()
        config2 = open(conf2,'a')
        getmultipleconfig(config2)

    net_connect.disconnect()

if 'single' in arg_mode:
    single_mode()
elif 'multiple' in arg_mode:
    multiple_mode()
else:
    print('bad mode')
    sys.exit(0)	

open(diff,'w').close
f3 = open(diff,'a')

with open(conf1,'r') as f1:
    with open(conf2,'r') as f2:
       differ = unified_diff(f1.readlines(),f2.readlines(),fromfile=conf1,tofile=conf2,n=0)
       for dline in differ:
          f3.write(dline)
f3.close()

cmd = 'zabbix_sender -z {0} -s "Network-scan" -k scan_port -o "$(cat /tmp/{1}/diff)"'.format(arg_zabbix, arg_ip)
subprocess.Popen(cmd, shell=True, executable='/bin/bash')

os.rename(conf2,conf1)
