"""
Hook loading utilities
"""
from __future__ import (print_function, absolute_import, unicode_literals,
                        division)

import abc

from dfs_sdk.dlogging import get_log

LOG = get_log(__name__)


def load_hooks(api, hooks):
    """
    Primary way to insert hooks into the SDK/API object

    Hooks should inherit from dfs_sdk.hooks.base:BaseHook.
    See dfs_sdk.hooks.cleanup:CleanupHandler for an example
    """
    for hook in hooks:
        context = api.context
        if context.version in hook.supported_versions():
            context.on_entity_create_hooks.append(hook.create_entity)
            context.on_entity_delete_hooks.append(hook.delete_entity)

            context.prepare_entity_hooks.append(hook.prepare_entity)
            context.prepare_endpoint_hooks.append(hook.prepare_endpoint)
        else:
            LOG.warn(
                "Hook does not support API version: {}.  Supported versions: "
                "{}".format(context.version, hook.supported_version()))


class BaseHook(object):

    @abc.abstractmethod
    def supported_versions(self):
        """ Called to check if hook supports current API version.
        Returns: list/tuple of supported API version strings
        Eg: ("v2.1", "v2.2", "v2.3")
        """
        pass

    @abc.abstractmethod
    def create_entity(self, entity):
        """ Called after an entity has been created on the system
        Returns: Modified entity (if any modification)
        """
        pass

    @abc.abstractmethod
    def delete_entity(self, entity):
        """ Called after an entity has been deleted from the system
        Returns: Modified entity (if any modification)
        """
        pass

    @abc.abstractmethod
    def prepare_entity(self, entity):
        """ Called to setup an entity object returned from a REST query
        Returns: Modified entity (if any modification)
        """
        pass

    @abc.abstractmethod
    def prepare_endpoint(self, endpoint):
        """ Called to setup an endpoint object
        Returns: Modified endpoint (if any modification)
        """
        pass
