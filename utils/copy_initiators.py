from dfs_sdk.scaffold import get_api
import pprint
import sys
import os

def copy_initiator(tenant, initiator):
    print("WARNING!")
    print("Copying initiator {:s} to tenant {:s}".format(initiator['name'], tenant['name']))
    if not input("Are you sure? (y/n): ").lower().strip()[:1] == "y": sys.exit('Aborted.')

    new_initiator = api.initiators.create(name=initiator['name'], id=initiator['id'], tenant=tenant['path'], force=True)

    print("Copied to initiator {:s}, id: {:s}".format(new_initiator['name'], new_initiator['id']))
    print("Done.")

def copy_initiator_prompt(tenant):
    print("Root tenant initiators:")
    initiators = api.initiators.list()

    for idx, initiator in enumerate(initiators):
        print("{:d} Name: {:s}, Id: {:s}".format(idx, initiator['name'],initiator['id']))

    while True:
        try:
            select = int(input("Select Initiator ID you want to copy: "))
            if select < 0 or select > len(initiators):
                print(">>> Must be >= 0 and <= {:d}, retry...".format(len(initiators)-1))
            else:
                break
        except KeyboardInterrupt:
            sys.exit('Aborted.')
        except:
            print (">>> Please try again, enter a number!")

    initiator = initiators[select]
    return initiator


api = get_api()

tenants = api.tenants.list()
root_tenant = tenants[0]
if root_tenant['name'] != 'root':
    sys.exit("Something is wrong, no root tenant?")

# Choose the subtenant of interest
print("Subtenants on this system:")
for idx, tenant in enumerate(tenants):
    print("{:d} Tenant: {:s}".format(idx, tenant['name']))

while True:
    try:
        select = int(input("Select tenant ID where you want to copy initiators: "))
        if select < 0 or select > len(tenants):
            print(">>> Must be > 0 and <= {:d}, retry...".format(len(tenants)-1))
        elif select == 0:
            print(">>> Cannot copy onto itself, please retry!")
        else:
            break
    except KeyboardInterrupt:
        sys.exit('Aborted.')
    except:
        print (">>> Please try again, enter a number!")

tenant = tenants[select]
print("Selected tenant {:s}".format(tenant['name']))

tenant_initiators = api.initiators.list(tenant=tenant['path'])
tenant_initiator_groups = api.initiator_groups.list(tenant=tenant['path'])

# DEBUG
# pprint.pprint(tenant_initiators)
# pprint.pprint(tenant_initiator_groups)

# List all app instances for this tenant
for ai in api.app_instances.list(tenant=tenant['path']):
    print("  App_instance: " + ai['name'])
    for si in ai.storage_instances.list(tenant=tenant['path']):
        print("    -Storage_instance: " + si['name'])
        for i in si.acl_policy.initiators.list(tenant=tenant['path']):
            print("        +Initiator: {:s} ({:s}) ({:s})".format(i['id'], i['name'], i['tenant']))
            if 'iqn' in si['access']:
                print("        +IQN: " + si['access']['iqn'])
        for i in si.acl_policy.initiator_groups.list(tenant=tenant['path']):
            print("        +Initiator group: {:s} ({:s})".format(i['name'], i['tenant']))

no_local_initiators = True
no_root_initiators = True
all_initiators_belong_to_subtenant = True
all_initiators_belong_to_root = True
for i in tenant_initiators:
    if i['tenant'] == '/root':
        no_root_initiators = False
        all_initiators_belong_to_subtenant = False
    if i['tenant'] == "/root/{:s}".format(tenant['name']):
        no_local_initiators = False
        all_initiators_belong_to_root = False

no_local_initiator_groups = True
no_root_initiator_groups = True
all_initiator_groups_belong_to_subtenant = True
all_initiator_groups_belong_to_root = True
for i in tenant_initiator_groups:
    if i['tenant'] == '/root':
        no_root_initiator_groups = False
        all_initiator_groups_belong_to_subtenant = False
    if i['tenant'] == "/root/{:s}".format(tenant['name']):
        no_local_initiator_groups = False
        all_initiator_groups_belong_to_root = False
# DEBUG
'''
if no_local_initiators:
    print("There are no local initiators for this tenant.")
if no_local_initiator_groups:
    print("There are no local initiator groups for this tenant.")
if all_initiators_belong_to_subtenant:
    print("all_initiators_belong_to_subtenant.")
if all_initiator_groups_belong_to_subtenant:
    print("all_initiator_groups_belong_to_subtenant.")
if all_initiators_belong_to_root:
    print("all_initiators_belong_to_root.")
if all_initiator_groups_belong_to_root:
    print("all_initiator_groups_belong_to_root.")
'''

# sanity checks
if not (all_initiators_belong_to_subtenant or no_local_initiators):
    print("We cannot have a mix of root and non-root tenant initiators, something is wrong, abort!")
    sys.exit("Something is wrong, mixed up initiators?")
if not (all_initiator_groups_belong_to_subtenant or no_local_initiator_groups):
    print("We cannot have a mix of root and non-root tenant initiator groups, something is wrong, abort!")
    sys.exit("Something is wrong, mixed up initiator groups?")


if no_local_initiators and no_local_initiator_groups:
    print("WARNING! WARNING! WARNING!")
    print("Attempting to copy all in use initiators (listed above) from root tenant to tenant {:s}".format(tenant['name']))
    print("This is going to be a one-shot operation that will interupt connectivity for a fraction of a second!")
    print("You will not have a chance to change your mind after this point!")
    if not input("ARE YOU ABSOLUTELY SURE? (y/n): ").lower().strip()[:1] == "y": sys.exit('Aborted.')

    for ai in api.app_instances.list(tenant=tenant['path']):
        print("  App_instance: " + ai['name'])
        for si in ai.storage_instances.list(tenant=tenant['path']):
            print("    -Storage_instance: " + si['name'])
            for i in si.acl_policy.initiators.list(tenant=tenant['path']):
                print("        +Initiator: {:s} ({:s}) ({:s})".format(i['id'], i['name'], i['tenant']))
                if 'iqn' in si['access']:
                    print("        +IQN: " + si['access']['iqn'])
                if i['tenant'] != '/root':
                    sys.exit("Something is wrong, initiator {:s} does not belong to /root tenant!".format(i['name']))
                new_initiator = api.initiators.create(name=i['name'], id=i['id'], tenant=tenant['path'], force=True)
                si.acl_policy.initiators.add(new_initiator, tenant=tenant['path'])
            for i in si.acl_policy.initiator_groups.list(tenant=tenant['path']):
                print("        +Initiator group: {:s} ({:s})".format(i['name'], i['tenant']))
                if i['tenant'] != '/root':
                    sys.exit("Something is wrong, initiator {:s} does not belong to /root tenant!".format(i['name']))
                members=[]
                for j in i['members']:
                    j_iqn = os.path.relpath(j['path'], '/initiators/')
                    print("Initiator: {:s}".format(j_iqn))
                    old_initiator = api.initiators.get(j_iqn)
                    new_initiator = api.initiators.create(name=old_initiator['name'], id=old_initiator['id'], tenant=tenant['path'], force=True)
                    element={}
                    element['path'] = new_initiator['path']
                    members.append(element)
                new_initiator_group = api.initiator_groups.create(name=i['name'], tenant=tenant['path'], members=members, force=True)
                si.acl_policy.initiator_groups.add(new_initiator_group, tenant=tenant['path'])      

    print("Final configuration for tenant {:s}".format(tenant['name']))
    for ai in api.app_instances.list(tenant=tenant['path']):
        print("  App_instance: " + ai['name'])
        for si in ai.storage_instances.list(tenant=tenant['path']):
            print("    -Storage_instance: " + si['name'])
            for i in si.acl_policy.initiators.list(tenant=tenant['path']):
                print("        +Initiator: {:s} ({:s}) ({:s})".format(i['id'], i['name'], i['tenant']))
                if 'iqn' in si['access']:
                    print("        +IQN: " + si['access']['iqn'])
                if i['tenant'] != "/root/{:s}".format(tenant['name']):
                    sys.exit("Something is wrong, initiator {:s} does not belong to {:s} tenant!".format(i['name'], tenant['name']))
            for i in si.acl_policy.initiator_groups.list(tenant=tenant['path']):
                print("        +Initiator group: {:s} ({:s})".format(i['name'], i['tenant']))
                if i['tenant'] != "/root/{:s}".format(tenant['name']):
                    sys.exit("Something is wrong, initiator {:s} does not belong to {:s} tenant!".format(i['name'], tenant['name']))

else:
    print("All initiators/groups are defined in this subtenant!")
    if not input("Do you want to copy an initiator from root tenant to this tenant? (y/n): ").lower().strip()[:1] == "y": sys.exit('Aborted.')
    initiator = copy_initiator_prompt(tenant)
    copy_initiator(tenant, initiator)