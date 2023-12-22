#  https://realpython.com/iterate-through-dictionary-python/

# interfaces = {'Admin/Voice Access': ['1/1/1', '1/1/2', '1/1/3', '1/1/4', '1/1/5', '1/1/6', '1/1/7', '1/1/8', '1/1/9', '1/1/10', '1/1/11', '1/1/12', '1/1/13', '1/1/14', '1/1/15', '1/1/16', '1/1/17', '1/1/18', '1/1/19', '1/1/20', '1/1/21', '1/1/23', '1/1/27', '1/1/44', '1/1/45', '1/1/48', '3/1/43', '3/1/45', '3/1/46', '3/1/47', '3/1/48'], 'Voice Only Access': ['1/1/46', '2/1/1', '2/1/2', '2/1/3', '2/1/4', '2/1/5', '2/1/6', '2/1/7', '2/1/8', '2/1/9', '2/1/10', '2/1/11', '2/1/12',
'2/1/13', '2/1/14', '2/1/15', '2/1/16', '2/1/17', '2/1/18', '2/1/19', '2/1/20', '2/1/21', '2/1/22', '2/1/23', '2/1/24', '2/1/25', '2/1/26', '2/1/27', '2/1/28', '2/1/29', '2/1/30', '2/1/31', '2/1/32', '2/1/33', '2/1/34', '2/1/35', '2/1/36', '2/1/37', '2/1/38', '2/1/39', '2/1/40', '2/1/41', '2/1/42', '2/1/43', '2/1/44', '2/1/45', '2/1/46', '2/1/47', '3/1/1', '3/1/2', '3/1/3', '3/1/4', '3/1/5', '3/1/6', '3/1/7', '3/1/8', '3/1/9', '3/1/10', '3/1/11', '3/1/12', '3/1/13', '3/1/14', '3/1/15', '3/1/16', '3/1/17', '3/1/18', '3/1/19', '3/1/20', '3/1/21', '3/1/22', '3/1/23', '3/1/24', '3/1/25', '3/1/26', '3/1/27', '3/1/28', '3/1/29', '3/1/30', '3/1/31', '3/1/32', '3/1/33', '3/1/34', '3/1/35', '3/1/36', '3/1/37', '3/1/38', '3/1/39', '3/1/40', '3/1/41', '3/1/42', '3/1/44'], 'WAP Access': ['1/1/22', '1/1/24', '1/1/25', '1/1/26', '1/1/28', '1/1/29', '1/1/30', '1/1/31', '1/1/32', '1/1/33', '1/1/34', '1/1/35', '1/1/36', '1/1/37', '1/1/38', '1/1/39', '1/1/40', '1/1/41', '1/1/42', '1/1/43', '2/1/48'], 'Facilities Access': ['1/1/47'], 'Admin/Voice Accessdisable': ['1/1/44']}

AdminVoice = '''   description Admin/Voice Access
    no shutdown
    persona custom admin_voice
    no routing
    vlan trunk native 101
    vlan trunk allowed 501
    spanning-tree bpdu-guard
    spanning-tree tcn-guard
    loop-protect
    port-access onboarding-method concurrent enable
    port-access allow-flood-traffic enable
    aaa authentication port-access allow-lldp-bpdu
    aaa authentication port-access client-limit 5
    aaa authentication port-access critical-role admin-voice
    aaa authentication port-access reject-role admin-voice
    aaa authentication port-access auth-role admin-voice
    aaa authentication port-access dot1x authenticator
        cached-reauth
        cached-reauth-period 86400
        max-eapol-requests 2
        max-retries 1
        reauth
        reauth-period 28800
        enable
    aaa authentication port-access mac-auth
        cached-reauth
        cached-reauth-period 86400
        quiet-period 30
        reauth
        reauth-period 28800
        enable'''

VoiceOnly = '''   description Voice Only Access
    no shutdown
    persona custom admin_voice
    no routing
    vlan trunk native 3999
    vlan trunk allowed 599
    spanning-tree bpdu-guard
    spanning-tree tcn-guard
    loop-protect
    port-access onboarding-method concurrent enable
    port-access allow-flood-traffic enable
    aaa authentication port-access allow-lldp-bpdu
    aaa authentication port-access client-limit 5
    aaa authentication port-access critical-role admin-voice
    aaa authentication port-access reject-role admin-voice
    aaa authentication port-access auth-role admin-voice
    aaa authentication port-access dot1x authenticator
        cached-reauth
        cached-reauth-period 86400
        max-eapol-requests 2
        max-retries 1
        reauth
        reauth-period 28800
        enable
    aaa authentication port-access mac-auth
        cached-reauth
        cached-reauth-period 86400
        quiet-period 30
        reauth
        reauth-period 28800
        enable
'''

WAPAccess = '''   description WAP/Access
    no shutdown
    persona custom Wireless_Access
    no routing
    vlan access 3999
    spanning-tree bpdu-guard
    spanning-tree tcn-guard
    loop-protect
    port-access onboarding-method concurrent enable
    aaa authentication port-access allow-lldp-bpdu
    aaa authentication port-access client-limit 2
    aaa authentication port-access critical-role wap
    aaa authentication port-access reject-role wap
    aaa authentication port-access auth-role wap
    aaa authentication port-access dot1x authenticator
        cached-reauth
        cached-reauth-period 86400
        max-eapol-requests 2
        max-retries 1
        reauth
        reauth-period 28800
        enable
    aaa authentication port-access mac-auth
        cached-reauth
        cached-reauth-period 86400
        quiet-period 30
        reauth
        reauth-period 28800
        enable
'''

FacAccess = '''   description Facilities Access
    no shutdown
    no routing
    vlan access 903
    qos trust dscp
    rate-limit broadcast 10000 kbps
    spanning-tree bpdu-guard
    spanning-tree loop-guard
    spanning-tree port-type admin-edge
    spanning-tree root-guard
    port-access onboarding-method concurrent enable
    port-access allow-flood-traffic enable
    aaa authentication port-access auth-precedence mac-auth dot1x
    aaa authentication port-access allow-lldp-bpdu
    aaa authentication port-access client-limit 2
    aaa authentication port-access critical-role facilities
    aaa authentication port-access reject-role facilities
    aaa authentication port-access auth-role facilities
    port-access allow-flood-traffic enable
    aaa authentication port-access dot1x authenticator
        cached-reauth
        cached-reauth-period 86400
        max-eapol-requests 2
        max-retries 1
        reauth
        reauth-period 28800
        enable
    aaa authentication port-access mac-auth
        cached-reauth
        cached-reauth-period 86400
        quiet-period 30
        reauth
        reauth-period 28800
        enable
'''

AccessDisable = '''   description Voice Only Access
    no shutdown
    persona custom admin_voice
    no routing
    vlan trunk native 3999
    vlan trunk allowed 599
    spanning-tree bpdu-guard
    spanning-tree tcn-guard
    loop-protect
    port-access onboarding-method concurrent enable
    port-access allow-flood-traffic enable
    aaa authentication port-access allow-lldp-bpdu
    aaa authentication port-access client-limit 5
    aaa authentication port-access critical-role admin-voice
    aaa authentication port-access reject-role admin-voice
    aaa authentication port-access auth-role admin-voice
    aaa authentication port-access dot1x authenticator
        cached-reauth
        cached-reauth-period 86400
        max-eapol-requests 2
        max-retries 1
        reauth
        reauth-period 28800
        enable
    aaa authentication port-access mac-auth
        cached-reauth
        cached-reauth-period 86400
        quiet-period 30
        reauth
        reauth-period 28800
        enable
'''
for key, value in interfaces.items():
    if key == 'Admin/Voice Access':
        for int in value:
            print(f'interface {int}\n {AdminVoice}')
    elif key == 'Voice Only Access':
            for int in value:
                print(f'interface {int}\n {VoiceOnly}')
    elif key == 'Facilities Access':
            for int in value:
                print(f'interface {int}\n {FacAccess}')
    elif key == 'Admin/Voice Accessdisable':
            for int in value:
                print(f'interface {int}\n {AccessDisable}')
    else:
        if key == 'WAP Access':
            for int in value:
                print(f'interface {int}\n {WAPAccess}')


            
#[' Admin/Voice Accessdisable', ' Admin/Voice Access', ' Voice Only Access', ' WAP Access', ' Facilities Access']