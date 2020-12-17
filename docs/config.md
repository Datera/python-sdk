Proposal
========
I'm proposing that we use a standard configuration file, something
simple that has all the information needed for each platform's "80%
usecase" and then having a tool that will generate the configuration for
each ecosystem from this.

Example (not set in stone):

    ```
    $ cat datera-config.json
    ```
    ```json
    {
        "mgmt_ip": "1.1.1.1",
        "username": "admin",
        "password": "password",
        "tenant": "SE-Openstack"
    }
    ```

This configuration file could be placed in a number of locations
    * passed in as a CLI flag
    * set via environment Variables
    * current directory
    * $HOME
    * $HOME/.config
    * /etc/datera
The tool would check each location for the configuration file in order
(which also determines precedence if multiple are found) then generate a
configuration for the specified ecosystem.

Example Tool Usage (also not set in stone):

    DMC --> Datera Make Ecosystem Config
    ```
    $ ./dmec --cinder
    # Place this at the end of your cinder.conf file
    [datera]
    volume_backend_name = datera
    volume_driver = cinder.volume.drivers.datera.datera_iscsi.DateraDriver
    san_ip = 1.1.1.1
    san_login = admin
    san_password = password
    datera_tenant_id = SE-Openstack
    datera_debug = True
    ```

This could also be done for the Kubernetes PV and PVC Yaml files.  This
would look something like:
    $./dmec --k8s-pv

    $./dmec --k8s-pvc

And whatever overly complex ways Kubernetes configures itself in the
future :)

Tools like the Python-SDK utils and DDCT would pull their connection
credentials from this config file and any future client-side tooling
would be able to use a single config file to get the connection info.


Templating
==========

Supporting the different options with the ecosystem would be as simple
as using reasonable defaults.

For a manual PV we would have a template like this:

```
=======================
kind: Persistent Volume
apiVersion: v1
metadata:
  name: {{name}}
  labels:
    manual: "true"
spec:
  capacity:
    storage: {{size}}Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  flexVolume:
    driver: "datera/iscsi"
    fsType: {{fsType}}
    secretRef:
      name: {{secret}}
    options:
      template: {{template}}
      retainPolicy: {{retain}}
      volumeID: {{vol-id}}
========================
```

The tool without arguments would generate the secret yaml for us (since
we'll always assume best practices) below is an example secret template

```
=================
apiVersion: v1
kind: Secret
metadata:
  name: {{secret-name}}
  namespace:
type: datera/iscsi
data:
  username: {{username-encoded}}
  password: {{password-encoded}}
  server: {{server-encoded}}
=================
```

Then similarly it will generate a PVC yaml

```
=======================
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: {{name}}-claim
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: {{size}}Gi
  selector:
    matchLabels:
      manual: "true"
======================
```

StorageClasses can be supported in a similar fashion

All this would be output to STDOUT will the fields filled in with
default values for anything not provided in the Datera config file or
via a CLI flag.

We could support either arbitrary nesting in the config file for
template values, or the same via a CLI flag.  Either is pretty easy to
implement.  We can also print the supported template overrides to make
it easy for the user.

Additionally we could print instructions for what to do with each yaml
file to make setting up any ecosystem with Datera dead simple



API loading process
===================

1. Config structure
    ```json
    {
        "mgmt_ip": "X.X.X.X",
        "username": "some_username",
        "password": "some_password",
        "tenant": "some_tenant",
        "api_version": "2.3"
    }
    ```
2. Environment Variables (sourceable file)
    ```bash
    DAT_MGMT=X.X.X.X
    DAT_USER=admin
    DAT_PASS=password
    DAT_TENANT=/root
    DAT_API=2.3
    ```
3. User executes script
    1. User provides credentials via CLI
    2. User provides credentials via environment variables
        1. DAT_MGMT
        2. DAT_USER
        3. DAT_PASS
        4. DAT_TENANT
        5. DAT_API
    3. User provides credentials via config file (.datera-config/datera-config)
        1. local directory
        2. $HOME folder
        3. $HOME/.config/datera folder
        4. /etc/datera folder
    4. User provides credentials via /etc/cinder/cinder.conf

4. This means load priority is
    1. CLI opts
    2. local folder config file
    3. $HOME folder config file
    4. $HOME/.config/datera folder config file
    5. /etc/datera config file
    6. /etc/cinder/cinder.conf

5. Config is loaded
6. API object is created from config
