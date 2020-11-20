"""
CleanupHandler class which maintains all the cleanup data for complete API
session.
"""
from __future__ import (print_function, absolute_import, unicode_literals,
                        division)

from dfs_sdk.dlogging import get_log
from dfs_sdk.exceptions import ApiError, ApiNotFoundError
from dfs_sdk.hooks.base import BaseHook

LOG = get_log(__name__)

__copyright__ = "Copyright 2018, Datera, Inc."


class CleanupHandler(BaseHook):
    """
    Class which manages all the objects that needs to be cleaned-up.
    """

    def __init__(self):
        """
        Object initialization
        """
        self._cleanup_paths = []  # List of path strings
        self._cleanup_map = {}  # map from path strings to Entity objects

    def supported_versions(self):
        return "v2.1", "v2.2", "v2.3"

    def create_entity(self, entity):
        """ Adding resource to the cleanup map
        """
        if not entity:
            return
        entity_path = entity.get('path', None)
        if not entity_path:
            return
        LOG.debug('Adding entity to cleanup map: %s', entity_path)
        if entity_path in self._cleanup_paths:
            if not isinstance(self._cleanup_map[entity_path], list):
                self._cleanup_map[entity_path] = [
                    self._cleanup_map[entity_path]]
            self._cleanup_paths.append(entity_path)
            self._cleanup_map[entity_path].append(entity)
            return
        self._cleanup_paths.append(entity_path)
        self._cleanup_map[entity_path] = entity

    def delete_entity(self, entity):
        """
        Removing entity from cleanup map
        """
        if not entity:
            return
        entity_path = entity.get('path', None)
        if not entity_path:
            return
        if entity_path not in self._cleanup_paths:
            return
        if isinstance(self._cleanup_map[entity_path], list) and len(
                self._cleanup_map[entity_path]) > 1:
            return
        LOG.debug('Removing entity from cleanup list: %s', entity_path)

        self._cleanup_paths.remove(entity_path)
        if isinstance(self._cleanup_map[entity_path], list):
            for ent in self._cleanup_map[entity_path]:
                if ent.tenant == entity.tenant:
                    index = self._cleanup_map[entity_path].index(ent)
                    break

            del self._cleanup_map[entity_path][index]
            return
        self._cleanup_map.pop(entity_path)

    def prepare_entity(self, entity):
        pass

    def prepare_endpoint(self, endpoint):
        pass

    def cleanup(self):
        """
        Cleanup all resources available in cleanup map. Cleanup will
        happen in reverse order from order in which they created.
        """
        for entity_path in self._cleanup_paths:
            entity_lst = self._cleanup_map[entity_path]
            if isinstance(entity_lst, list):
                for entity in entity_lst:
                    if 'admin_state' in entity:
                        try:
                            if 'tenant' in entity:
                                entity.set(admin_state='offline', force=True,
                                           tenant=entity['tenant'])
                            else:
                                entity.set(admin_state='offline', force=True)
                        except ApiError:
                            LOG.warning(
                                "Could not set entity offline: " + entity_path)
            else:
                entity = entity_lst
                if 'admin_state' in entity:
                    try:
                        if 'tenant' in entity:
                            entity.set(admin_state='offline', force=True,
                                       tenant=entity['tenant'])
                        else:
                            entity.set(admin_state='offline', force=True)
                    except ApiError:
                        LOG.warning(
                            "Could not set entity offline: " + entity_path)

        while self._cleanup_paths:
            entity_path = self._cleanup_paths.pop()  # remove from right
            entity_lst = self._cleanup_map[entity_path]
            if isinstance(entity_lst, list):
                if len(entity_lst) == 1:
                    self._cleanup_map.pop(entity_path)

                for entity in entity_lst:
                    try:
                        LOG.debug('Deleting entity: %s', entity_path)
                        if 'tenant' in entity:
                            entity.delete(tenant=entity['tenant'])
                        else:
                            entity.delete()
                    except ApiNotFoundError:
                        LOG.debug(
                            "Cannot delete entity. Entity does not exist: %s",
                            entity_path)
            else:
                entity_lst = self._cleanup_map.pop(entity_path)
                entity = entity_lst
                try:
                    LOG.debug('Deleting entity: %s', entity_path)
                    if 'tenant' in entity:
                        entity.delete(tenant=entity['tenant'])
                    else:
                        entity.delete()
                except ApiNotFoundError:
                    LOG.debug(
                        "Cannot delete entity. Entity does not exist: %s",
                        entity_path)
