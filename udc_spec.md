# Universal Datera Config Specification (UDC Spec)

## Version

v1.0.0-alpha-1

## What is UDC


UDC is a definition for how to store and load access credentials and information
related to the access of a Datera Storage Cluster.  This in short consists
of a file format, directory locations, a lookup/override preference and
environment variables/cli arguments

## Why do we need this?

With the explosion of Ecosystem tools, driver and plugins there needs to be
a consistent way for users to specify the credentials for a Datera Storage
Cluster.  This eases the transition between ecosystem tools since, ideally,
they will all support the full extent of UDC.  Thus configuring UDC for one
tool/driver will cause all others to be configured as well on the same system.

## Spec

### File format

The file format for a valid UDC configuration is a five key json file like
the following
```json
{
      "mgmt_ip": "1.1.1.1",
      "username": "admin",
      "password": "password",
      "tenant": "/root",
      "api_version": "2.2",
      "ldap": ""
}
```

Where the following keys are defined:

* ``mgmt_ip`` -- The management ip of the Datera Cluster.
* ``username`` -- The username of the users's Datera cluster account.
* ``password`` -- The password of the users's Datera cluster account.
* ``tenant`` -- (optional) The tenant/subtenant under the user's Datera cluster account
* ``api_version`` -- (optional) The API version desired for accessing the cluster
* ``ldap`` -- (optional) The LDAP server configured on the Datera cluster for additional authentication

All values are provided as double-quoted strings
Additional keys may be added in the future, but no key may be removed from
the specification.  Instead, deprecated keys can be made "optional".

### Valid Filenames

Valid UDC files MUST be named one of the following filenames.  The filename
priority order is the order listed below.

* ``.datera-config``
* ``datera-config``
* ``.datera-config.json``
* ``datera-config.json``

### Valid Host Directories

Valid UDC files may be placed in a number of directories on the host.  These
directories have a specified lookup order/priority.  The priority is the order
listed below

* current working directory
* Unix Home (``~``)
* Unix Config Home (``~/datera/``)
* Unix Site Config Home (``/etc/datera/``)

This priority order allows for a user to specify a UDC config at multiple levels
of the host filesystem and override lower priority levels with higher priority
levels.

For example, if a user placed a valid UDC file in the ``/etc/datera`` location
and then placed another in the current working directory.  The file in the
current working directory takes precedence.

### Environment Variables

* ``DAT_MGMT`` -- equivalent to ``"mgmt_ip"``
* ``DAT_USER`` -- equivalent to ``"username"``
* ``DAT_PASS`` -- equivalent to ``"password"``
* ``DAT_TENANT`` -- equivalent to ``"tenant"``
* ``DAT_API`` -- equivalent to ``"api_version"``
* ``DAT_LDAP`` -- equivalent to ``"ldap"``

Any environment variable will override the equivalent UDC key in a loaded UDC
file.

For example if you had the following UDC file
```json
{
      "mgmt_ip": "1.1.1.1",
      "username": "admin",
      "password": "password",
      "tenant": "/root",
      "api_version": "2.2",
      "ldap": ""
}
```
And also set ``DAT_MGMT=2.2.2.2``, then the loaded UDC config would be equivalent
to
```json
{
      "mgmt_ip": "2.2.2.2",
      "username": "admin",
      "password": "password",
      "tenant": "/root",
      "api_version": "2.2",
      "ldap": ""
}
```
All keys may be specified this way.  A UDC file is not necessary if all
non-optional keys are provided via environment variables.

### CLI Arguments

Any UDC compliant application may optionally provide CLI arguments for
UDC keys.  The names for these are up to the CLI application and UDC compliant
applications may choose to not provide them at all.

### Optional UDC Credential Loading

UDC compliant applications may extend UDC functionality by loading UDC information
from an alternative location ONLY if that loading is performed at the lowest
possible priority (meaning AFTER no valid UDC file has been found at any
valid UDC location).  They MUST still allow for overriding UDC keys via environment
variables.

An example of this is the python-sdk UDC implementation.  It will optionally
try to read a cinder.conf file on the host AFTER no valid UDC file is found
on the host.  This is provided as an ease-of-use feature, but is not a part
of the official UDC spec.

### Optional Keys

An "optional" key is one that can be omitted from the Datera UDC file, environment
variables or CLI arguments and a default value will be provided.

Current optional keys and their default values:

* ``tenant``: ``"/root"``
* ``api_version``: ``"2.2"``
* ``ldap``: ``""``

#### UDC To Driver Specific Config

Some Ecosystems and applications do not have the luxury of being able to be
UDC compliant.  If this is the case, the driver/application should provide a
utility with which to generate their needed configuration from a UDC file.
If possible this integration should be added to a common utility like DDCT
which is already UDC compliant. (github.com/Datera/ddct)

### Potential Future Improvements

#### Partial Override

Currently the spec only specifies that UDC values are overridden on a per-file
basis.  Meaning that if you specify a file at /etc/datera and one in the current
directory the entire file at the current directory takes precedence.  It might
be worth exploring allowing for partial UDC files in high priority locations
that will only override their contents, while pulling missing keys from
lower priority locations until the entire UDC config is assembled

#### Multi-tenant UDC

Currently each UDC file can only support a single tenant.  It might be worth
exploring the possibility of having multiple tenants in a UDC file or a consistent
way in which UDC compliant applications allow for switching tenants on load
or during operation.
