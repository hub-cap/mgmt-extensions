# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova import compute
from nova import log as logging
from nova.api.openstack.compute.servers import ServersTemplate
from nova.api.openstack.compute.views import servers as server_views
from nova.api.openstack.compute.servers import ServerTemplate


LOG = logging.getLogger(__name__)
authorize = extensions.extension_authorizer('compute', 'rdservers')


class Controller(object):

    def __init__(self):
        self.compute_api = compute.API()
        self.server_view = server_views.ViewBuilder()

    @wsgi.serializers(xml=ServersTemplate)
    def index(self, req, deleted=False):
        """ Returns all local instances, optionally filtered by deleted status."""
        context = req.environ['nova.context']
        authorize(context)
        search_opts = {'deleted': deleted}
        instances = self.compute_api.get_all(context, search_opts=search_opts)
        servers = []

        for instance in instances:
            server = {'id': instance.get('uuid'),
                      'local_id': instance.get('id'),
                      'name': instance.get('display_name'),
                      'status': self.server_view._get_vm_state(instance),
                      'host': instance.get('host'),
                      'deleted': instance.get('deleted'),
                      'deleted_at':instance.get('deleted_at'),
                      'tenant_id': instance.get('project_id')}
            servers.append(server)
        return {'servers': servers}

    @wsgi.serializers(xml=ServerTemplate)
    def show(self, req, id):
        """ Returns mgmt instance details."""
        context = req.environ['nova.context']
        authorize(context)
        instance = self.compute_api.get(context, id)
        server = {'id': instance.get('uuid'),
                  'local_id': instance.get('id'),
                  'name': instance.get('display_name'),
                  'status': self.server_view._get_vm_state(instance),
                  'host': instance.get('host'),
                  'deleted': instance.get('deleted'),
                  'deleted_at':instance.get('deleted_at'),
                  'tenant_id': instance.get('project_id')}
        return {'server': server}


class Rdservers(extensions.ExtensionDescriptor):
    """Admin-only access to rdservers"""
    name = "Rdservers"
    alias = "rd-servers"
    namespace = "http://docs.openstack.org/compute/ext/rdservers/api/v1.1"
    updated = "2011-12-23T00:00:00+00:00"

    def get_resources(self):
        res = extensions.ResourceExtension('rd-servers', Controller())
        return [res]
