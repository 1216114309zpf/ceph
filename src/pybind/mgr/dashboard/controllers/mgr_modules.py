# -*- coding: utf-8 -*-
from __future__ import absolute_import

from . import ApiController, RESTController
from .. import mgr
from ..security import Scope
from ..services.ceph_service import CephService
from ..services.exception import handle_send_command_error
from ..tools import find_object_in_list, str_to_bool


@ApiController('/mgr/module', Scope.CONFIG_OPT)
class MgrModules(RESTController):
    managed_modules = ['telemetry']

    def list(self):
        """
        Get the list of managed modules.
        :return: A list of objects with the fields 'name' and 'enabled'.
        :rtype: list
        """
        result = []
        mgr_map = mgr.get('mgr_map')
        for module_config in mgr_map['available_modules']:
            if self._is_module_managed(module_config['name']):
                result.append({'name': module_config['name'], 'enabled': False})
        for name in mgr_map['modules']:
            if self._is_module_managed(name):
                obj = find_object_in_list('name', name, result)
                obj['enabled'] = True
        return result

    def get(self, module_name):
        """
        Retrieve the values of the persistent configuration settings.
        :param module_name: The name of the Ceph Mgr module.
        :type module_name: str
        :return: The values of the module options.
        :rtype: dict
        """
        assert self._is_module_managed(module_name)
        options = self._get_module_options(module_name)
        result = {}
        for name, option in options.items():
            result[name] = mgr.get_module_option_ex(module_name, name,
                                                    option['default_value'])
        return result

    @RESTController.Resource('PUT')
    def set(self, module_name, config):
        """
        Set the values of the persistent configuration settings.
        :param module_name: The name of the Ceph Mgr module.
        :type module_name: str
        :param config: The values of the module options to be stored.
        :type config: dict
        """
        assert self._is_module_managed(module_name)
        options = self._get_module_options(module_name)
        for name in options.keys():
            if name in config:
                mgr.set_module_option_ex(module_name, name, config[name])

    @RESTController.Resource('POST')
    @handle_send_command_error('mgr_modules')
    def enable(self, module_name):
        """
        Enable the specified Ceph Mgr module.
        """
        assert self._is_module_managed(module_name)
        CephService.send_command(
            'mon', 'mgr module enable', module=module_name)

    @RESTController.Resource('POST')
    @handle_send_command_error('mgr_modules')
    def disable(self, module_name):
        """
        Disable the specified Ceph Mgr module.
        """
        assert self._is_module_managed(module_name)
        CephService.send_command(
            'mon', 'mgr module disable', module=module_name)

    def _is_module_managed(self, module_name):
        """
        Check if the specified Ceph Mgr module is managed by this service.
        :param module_name: The name of the Ceph Mgr module.
        :type module_name: str
        :return: Returns ``true`` if the Ceph Mgr module is managed by
            this service, otherwise ``false``.
        :rtype: bool
        """
        return module_name in self.managed_modules

    def _get_module_config(self, module_name):
        """
        Helper function to get detailed module configuration.
        :param module_name: The name of the Ceph Mgr module.
        :type module_name: str
        :return: The module information, e.g. module name, can run,
            error string and available module options.
        :rtype: dict or None
        """
        mgr_map = mgr.get('mgr_map')
        return find_object_in_list('name', module_name,
                                   mgr_map['available_modules'])

    def _get_module_options(self, module_name):
        """
        Helper function to get the module options.
        :param module_name: The name of the Ceph Mgr module.
        :type module_name: str
        :return: The module options.
        :rtype: dict
        """
        options = self._get_module_config(module_name)['module_options']
        # Workaround a possible bug in the Ceph Mgr implementation. The
        # 'default_value' field is always returned as a string.
        for option in options.values():
            if option['type'] == 'str':
                if option['default_value'] == 'None':
                    option['default_value'] = ''
            elif option['type'] == 'bool':
                option['default_value'] = str_to_bool(option['default_value'])
            elif option['type'] == 'float':
                option['default_value'] = float(option['default_value'])
            elif option['type'] in ['uint', 'int', 'size', 'secs']:
                option['default_value'] = int(option['default_value'])
        return options
