# Copyright 2011 OpenStack LLC.
# All Rights Reserved.
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
#    under the License.

import webob.exc

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
from nova.api.openstack.compute.views import servers as server_views
from nova.auth import manager
from nova.db import api as dbapi
from nova import compute
from nova import exception
from nova import flags
from nova import log as logging


FLAGS = flags.FLAGS
LOG = logging.getLogger(__name__)
authorize = extensions.extension_authorizer('compute', 'rdhosts')


class RdhostsTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('rdhost', selector='rdhost')
        root.set('id', 'id')
        root.set('name', 'name')
        root.set('description', 'description')
        root.set('manager', 'manager')

        return xmlutil.MasterTemplate(root, 1)


def _translate_keys(rd_host):
    return dict(id=rd_host.id,
                name=rd_host.name,
                description=rd_host.description,
                manager=rd_host.project_manager_id)


class Controller(object):

    def __init__(self):
        self.manager = manager.AuthManager()
        self.compute_api = compute.API()
        self.server_view = server_views.ViewBuilder()

    def index(self, req):
        """List all the hosts on the system"""
        LOG.info("List all the nova-compute hosts in the system")
        ctxt = req.environ['nova.context']
        authorize(ctxt)
        LOG.debug("%s - %s", req.environ, req.body)
        services = dbapi.service_get_all_compute_sorted(ctxt)
        # services looks like (Service(object), Decimal('0'))
        # must convert from Decimal('0') to int() because no JSON repr
        hosts = [{'name':srv[0].host,
                  'instanceCount':int(srv[1])}
                  for srv in services]
        return {'hosts': hosts}


    @wsgi.serializers(xml=RdhostsTemplate)
    def show(self, req, id):
        """List all the instances on the host given a host name."""
        ctxt = req.environ['nova.context']
        authorize(ctxt)
        try:
            LOG.info("List the info on nova-compute '%s'" % id)
            LOG.debug("%s - %s", req.environ, req.body)
            instances = dbapi.show_instances_on_host(ctxt, id)
            instances = [{'uuid': c.uuid,
                          'name': c.display_description,
                          'status': c.vm_state} for c in instances]
            compute_node = dbapi.compute_node_get_by_host(ctxt, id)
            total_ram = float(compute_node.memory_mb)
            used_ram = float(compute_node.memory_mb_used)
            percent = int(round((used_ram / total_ram) * 100))
            return {'host': {'name': id,
                             'percentUsed': percent,
                             'totalRAM': int(total_ram),
                             'usedRAM': int(used_ram),
                             'instances': instances}}
        except exception.ComputeHostNotFound:
            raise webob.exc.HTTPNotFound()


class Rdhosts(extensions.ExtensionDescriptor):
    """Admin-only access to rdhosts"""

    name = "Rdhosts"
    alias = "rd-hosts"
    namespace = "http://docs.openstack.org/compute/ext/rdhosts/api/v1.1"
    updated = "2011-12-23T00:00:00+00:00"

    def get_resources(self):
        res = extensions.ResourceExtension('rd-hosts', Controller())
        return [res]
