'''
Workspace for config snippets
prints interfaces that are not shutdown
'''

import re
from ciscoconfparse import CiscoConfParse
parse = CiscoConfParse('01_swart6rSTORERM-running-config.txt', syntax='ios')

# WapInterfaces = []
# for io in parse.find_objects('^interface'):
#     if io and any('WAP Access' in co.text for co in io.children):
#         # print(io.text)
#         if 'Gigabit' in io.text:
#             WapInterfaces.append(io.text.split('GigabitEthernet')[-1])
        
#         # for co in io.children:
#         #    print(co.text)
# print('WapInterfaces:')        
# print(WapInterfaces)

# Grabs all descriptions and puts them in a list
#descriptionList = ['Security Access', 'Admin/Voice Access', 'WAP Access', 'Facilities Access']
descriptionList = []
# TotalInterfaces = 0
for io in parse.find_objects('^interface'):
    pattern = r'GigabitEthernet(\d+)/0'
    match = re.search(pattern, io.text)
    # print(io.text)
    # print(match)
    if match:
        for co in io.children:
            if ' description' in co.text:
                descriptionList.append(co.text.split('description')[-1])
descriptionList = list(set(descriptionList))
print(descriptionList)

def getDeviceInterfaces(parse, description):
    deviceInterfaces = []
    for io in parse.find_objects('^interface'):
        if io and any(description in co.text for co in io.children):
            # print(io.text)
            if 'Gigabit' in io.text:
                deviceInterfaces.append(io.text.split('GigabitEthernet')[-1])
            
            # for co in io.children:
            #    print(co.text)
    newDescription = description
    return newDescription, deviceInterfaces

def replace_interfaces(interface_list):
    pattern = r'(\d+)/0/(\d+)'
    new_interface_list = []
    for interface in interface_list:
        new_interface = re.sub(pattern, r'\1/1/\2', interface)
        new_interface_list.append(new_interface)
    return new_interface_list

aruba_interface_dict = {}
for item in descriptionList:
    description, deviceInterfaces = getDeviceInterfaces(parse, description = item)
    print(description, 'Interfaces:')        
    print(deviceInterfaces)
    aruba_interfaces = replace_interfaces(deviceInterfaces)
    print(aruba_interfaces)
    aruba_interface_dict[description.strip()] = aruba_interfaces
    # description.strip().replace('/','').replace(' ','') =

#aruba_interface_dict = {desc: iface for desc, iface in zip(descriptionList,)}
print('Dictionary of interfaces:\n', aruba_interface_dict)




# for io in parse.find_objects('^interface'):
#     if io and not any('shutdown' in co.text for co in io.children):
#         print(io.text)
#         for co in io.children:
#            print(co.text)

# #prints just eigrp config
# print('EIGRP INTERFACE CONFIGURATION')
# for io in parse.find_objects('^interface'):
#     if io and any('eigrp 100' in co.text for co in io.children):
#         print(io.text)
#         for co in io.children:
#            if 'eigrp 100' in co.text:
#                print(co.text)

# #prints removal of eirgp config
# print('\n\nEIGRP INTERFACE CONFIGURATION REMOVAL')
# for io in parse.find_objects('^interface'):
#     if io and any('eigrp 100' in co.text for co in io.children):
#         print(io.text)
#         for co in io.children:
#            if 'eigrp 100' in co.text:
#                print(co.uncfgtext)

#Grabs all VRF's and puts them in a list
# VrfList = []
# TotalInterfaces = 0
# for io in parse.find_objects('^ip vrf'):
#     VrfList.append(io.text.split(' ')[-1])
# print(VrfList)

# #prints OSPF config add on
# print('ADDS OSPF INTERFACE CONFIGURATION')
# for io in parse.find_objects('^interface'):
#     if io and any('training' in co.text for co in io.children):
#         print(io.text)
#         for co in io.children:
#            if 'vrf forwarding' in co.text:
#                print('#', co.text)
#         print(' ip ospf authentication message-digest')
#         print(' ip ospf message-digest-key 1 md5 7 01040E1C0F2E143E371A6C2B2B0030')
#         print(' ip ospf dead-interval 3')
#         print(' ip ospf hello-interval 1')
#         print(' ip ospf 2 area 0')

def generate_ospf_config(parse, vrf_name, ospf_process):
    global TotalInterfaces
    ospf_config = ''
    ospf_config += '# ADDS OSPF INTERFACE CONFIGURATION\n'
    for io in parse.find_objects('^interface'):
        if io and not any('shutdown' in co.text for co in io.children):
            if io and any(vrf_name in co.text for co in io.children):
                TotalInterfaces += 1
                ospf_config += io.text + '\n'
                ospf_config += '# ' + vrf_name + ' VRF \n'
                ospf_config += ' ip ospf authentication message-digest\n'
                ospf_config += ' ip ospf message-digest-key 1 md5 7 01040E1C0F2E143E371A6C2B2B0030\n'
                ospf_config += ' ip ospf dead-interval 3\n'
                ospf_config += ' ip ospf hello-interval 1\n'
                ospf_config += f' ip ospf {ospf_process} area 0\n'
    return ospf_config

def generate_default_ospf_config(parse, vrf_name, ospf_process):
    global TotalInterfaces
    ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    ospf_config = ''
    ospf_config += '# ADDS OSPF INTERFACE CONFIGURATION\n'
    for io in parse.find_objects('^interface'):
        if io and not any('shutdown' in co.text for co in io.children):
            if io and not any(vrf in co.text for co in io.children for vrf in VrfList):
                if io and any(re.search(ip_pattern, co.text) for co in io.children):
                    TotalInterfaces += 1
                    ospf_config += io.text + '\n'
                    ospf_config += '# ' + vrf_name + ' VRF \n'
                    ospf_config += ' ip ospf authentication message-digest\n'
                    ospf_config += ' ip ospf message-digest-key 1 md5 7 01040E1C0F2E143E371A6C2B2B0030\n'
                    ospf_config += ' ip ospf dead-interval 3\n'
                    ospf_config += ' ip ospf hello-interval 1\n'
                    ospf_config += f' ip ospf {ospf_process} area 0\n'
    return ospf_config

# ospf_config = generate_ospf_config(parse, vrf_name= 'training', ospf_process= '2')
# print(ospf_config)

# ospf_config = generate_ospf_config(parse, vrf_name= 'voice', ospf_process= '3')
# print(ospf_config)

# ospf_config = generate_ospf_config(parse, vrf_name= 'voicesvr', ospf_process= '103')
# print(ospf_config)

# ospf_config = generate_ospf_config(parse, vrf_name= 'Mgmt-Zone', ospf_process= '4')
# print(ospf_config)

# ospf_config = generate_ospf_config(parse, vrf_name= 'datacenter-zone', ospf_process= '5')
# print(ospf_config)

# ospf_config = generate_ospf_config(parse, vrf_name= 'trnDatacenter-Zone', ospf_process= '6')
# print(ospf_config)

# ospf_config = generate_ospf_config(parse, vrf_name= 'sled-zone', ospf_process= '7')
# print(ospf_config)

# ospf_config = generate_default_ospf_config(parse, vrf_name= 'default', ospf_process= '1')
# print(ospf_config)

# print(TotalInterfaces)
