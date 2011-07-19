# Copyright 2011 GRNET S.A. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
# 
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from pithos.lib.client import Pithos_Client, Fault
import unittest
from django.utils import simplejson as json
from xml.dom import minidom
from StringIO import StringIO
import time as _time
import types
import hashlib
import os
import mimetypes
import random
import datetime
import string
import re

DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
                "%A, %d-%b-%y %H:%M:%S GMT",
                "%a, %d %b %Y %H:%M:%S GMT"]

DEFAULT_HOST = 'pithos.dev.grnet.gr'
#DEFAULT_HOST = '127.0.0.1:8000'
DEFAULT_API = 'v1'
DEFAULT_USER = 'test'
DEFAULT_AUTH = '0000'

class BaseTestCase(unittest.TestCase):
    #TODO unauthorized request
    def setUp(self):
        self.client = Pithos_Client(DEFAULT_HOST,
                                    DEFAULT_AUTH,
                                    DEFAULT_USER,
                                    DEFAULT_API)
        self.invalid_client = Pithos_Client(DEFAULT_HOST,
                                                  DEFAULT_AUTH,
                                                  'invalid',
                                                  DEFAULT_API)
        #self.headers = {
        #    'account': ('x-account-container-count',
        #                'x-account-bytes-used',
        #                'last-modified',
        #                'content-length',
        #                'date',
        #                'content_type',
        #                'server',),
        #    'object': ('etag',
        #               'content-length',
        #               'content_type',
        #               'content-encoding',
        #               'last-modified',
        #               'date',
        #               'x-object-manifest',
        #               'content-range',
        #               'x-object-modified-by',
        #               'x-object-version',
        #               'x-object-version-timestamp',
        #               'server',),
        #    'container': ('x-container-object-count',
        #                  'x-container-bytes-used',
        #                  'content_type',
        #                  'last-modified',
        #                  'content-length',
        #                  'date',
        #                  'x-container-block-size',
        #                  'x-container-block-hash',
        #                  'x-container-policy-quota',
        #                  'x-container-policy-versioning',
        #                  'server',
        #                  'x-container-object-meta',
        #                  'x-container-policy-versioning',
        #                  'server',)}
        #
        #self.contentTypes = {'xml':'application/xml',
        #                     'json':'application/json',
        #                     '':'text/plain'}
        self.extended = {
            'container':(
                'name',
                'count',
                'bytes',
                'last_modified'),
            'object':(
                'name',
                'hash',
                'bytes',
                'content_type',
                'content_encoding',
                'last_modified',)}
        self.return_codes = (400, 401, 404, 503,)
    
    def tearDown(self):
        for c in self.client.list_containers():
            for o in self.client.list_objects(c):
                self.client.delete_object(c, o)
            self.client.delete_container(c)
    
    def assert_status(self, status, codes):
        l = [elem for elem in self.return_codes]
        if type(codes) == types.ListType:
            l.extend(codes)
        else:
            l.append(codes)
        self.assertTrue(status in l)
    
    #def assert_list(self, path, entity, limit=10000, format='text', params=None, **headers):
    #    status, headers, data = self.client.get(path, format=format,
    #                                            headers=headers, params=params)
    #    
    #    self.assert_status(status, [200, 204, 304, 412])
    #    if format == 'text':
    #        data = data.strip().split('\n') if data else []
    #        self.assertTrue(len(data) <= limit)
    #    else:
    #        exp_content_type = self.contentTypes[format]
    #        self.assertEqual(headers['content_type'].find(exp_content_type), 0)
    #        #self.assert_extended(data, format, entity, limit)
    #        if format == 'json':
    #            data = json.loads(data) if data else []
    #        elif format == 'xml':
    #            data = minidom.parseString(data)
    #    return status, headers, data
    
    #def assert_headers(self, headers, type, **exp_meta):
    #    prefix = 'x-%s-meta-' %type
    #    system_headers = [h for h in headers if not h.startswith(prefix)]
    #    for k,v in headers.items():
    #        if k in system_headers:
    #            self.assertTrue(k in headers[type])
    #        elif exp_meta:
    #            k = k.split(prefix)[-1]
    #            self.assertEqual(v, exp_meta[k])
    
    def assert_extended(self, data, format, type, size):
        if format == 'xml':
            self._assert_xml(data, type, size)
        elif format == 'json':
            self._assert_json(data, type, size)
    
    def _assert_json(self, data, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in self.extended[type]]
        self.assertTrue(len(data) <= size)
        for item in info:
            for i in data:
                if 'subdir' in i.keys():
                    continue
                self.assertTrue(item in i.keys())
    
    def _assert_xml(self, data, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in self.extended[type]]
        try:
            info.remove('content_encoding')
        except ValueError:
            pass
        xml = data
        entities = xml.getElementsByTagName(type)
        self.assertTrue(len(entities) <= size)
        for e in entities:
            for item in info:
                self.assertTrue(e.hasAttribute(item))
    
    def assert_raises_fault(self, status, callableObj, *args, **kwargs):
        """
        asserts that a Fault with a specific status is raised
        when callableObj is called with the specific arguments
        """
        try:
            callableObj(*args, **kwargs)
            self.fail('Should never reach here')
        except Fault, f:
            self.failUnless(f.status == status)
    
    def assert_container_exists(self, container):
        """
        asserts the existence of a container
        """
        try:
            self.client.retrieve_container_metadata(container)
        except Fault, f:
            self.failIf(f.status == 404)
    
    def assert_object_exists(self, container, object):
        """
        asserts the existence of an object
        """
        try:
            self.client.retrieve_object_metadata(container, object)
        except Fault, f:
            self.failIf(f.status == 404)
    
    def assert_object_not_exists(self, container, object):
        """
        asserts there is no such an object
        """
        self.assert_raises_fault(404, self.client.retrieve_object_metadata,
                                 container, object)
    
    def upload_random_data(self, container, name, length=1024, type=None,
                           enc=None, **meta):
        data = get_random_data(length)
        return self.upload_data(container, name, data, type, enc, **meta)
    
    def upload_data(self, container, name, data, type=None, enc=None, etag=None,
                    **meta):
        obj = {}
        obj['name'] = name
        try:
            obj['data'] = data
            obj['hash'] = compute_md5_hash(obj['data'])
            
            args = {}
            args['etag'] = etag if etag else obj['hash']
            
            guess = mimetypes.guess_type(name)
            type = type if type else guess[0]
            enc = enc if enc else guess[1]
            args['content_type'] = type if type else 'plain/text'
            args['content_encoding'] = enc if enc else None
            
            obj['meta'] = args
            
            path = '/%s/%s' % (container, name)
            self.client.create_object(container, name, StringIO(obj['data']),
                                      meta, **args)
            
            return obj
        except IOError:
            return

class AccountHead(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in self.containers:
            self.client.create_container(item)
    
    def tearDown(self):
        self.client.delete_account_metadata(['foo'])
        BaseTestCase.tearDown(self)
    
    def test_get_account_meta(self):
        meta = self.client.retrieve_account_metadata()
        
        containers = self.client.list_containers()
        l = str(len(containers))
        self.assertEqual(meta['x-account-container-count'], l)
        size = 0
        for c in containers:
            m = self.client.retrieve_container_metadata(c)
            size = size + int(m['x-container-bytes-used'])
        self.assertEqual(meta['x-account-bytes-used'], str(size))
    
    def test_get_account_401(self):
        self.assert_raises_fault(401,
                                 self.invalid_client.retrieve_account_metadata)
    
    def test_get_account_meta_until(self):
        t = datetime.datetime.utcnow()
        past = t - datetime.timedelta(minutes=-15)
        past = int(_time.mktime(past.timetuple()))
        
        meta = {'foo':'bar'}
        self.client.update_account_metadata(**meta)
        meta = self.client.retrieve_account_metadata(restricted=True,
                                                     until=past)
        self.assertTrue('foo' not in meta)
        
        meta = self.client.retrieve_account_metadata(restricted=True)
        self.assertTrue('foo' in meta)
    
    def test_get_account_meta_until_invalid_date(self):
        meta = {'foo':'bar'}
        self.client.update_account_metadata(**meta)
        meta = self.client.retrieve_account_metadata(restricted=True,
                                                     until='kshfksfh')
        self.assertTrue('foo' in meta)

class AccountGet(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        #create some containers
        self.containers = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in self.containers:
            self.client.create_container(item)
    
    def test_list(self):
        #list containers
        containers = self.client.list_containers()
        self.assertEquals(self.containers, containers)
    
    def test_list_401(self):
        self.assert_raises_fault(401, self.invalid_client.list_containers)
    
    def test_list_with_limit(self):
        limit = 2
        containers = self.client.list_containers(limit=limit)
        self.assertEquals(len(containers), limit)
        self.assertEquals(self.containers[:2], containers)
    
    def test_list_with_marker(self):
        l = 2
        m = 'bananas'
        containers = self.client.list_containers(limit=l, marker=m)
        i = self.containers.index(m) + 1
        self.assertEquals(self.containers[i:(i+l)], containers)
        
        m = 'oranges'
        containers = self.client.list_containers(limit=l, marker=m)
        i = self.containers.index(m) + 1
        self.assertEquals(self.containers[i:(i+l)], containers)
    
    def test_list_json_with_marker(self):
        l = 2
        m = 'bananas'
        containers = self.client.list_containers(limit=l, marker=m, format='json')
        self.assert_extended(containers, 'json', 'container', l)
        self.assertEqual(containers[0]['name'], 'kiwis')
        self.assertEqual(containers[1]['name'], 'oranges')
    
    def test_list_xml_with_marker(self):
        l = 2
        m = 'oranges'
        xml = self.client.list_containers(limit=l, marker=m, format='xml')
        #self.assert_extended(xml, 'xml', 'container', l)
        nodes = xml.getElementsByTagName('name')
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].childNodes[0].data, 'pears')
    
    def test_if_modified_since(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #add a new container
        self.client.create_container('dummy')
        
        for f in DATE_FORMATS:
            past = t2.strftime(f)
            try:
                c = self.client.list_containers(if_modified_since=past)
                self.assertEqual(len(c), len(self.containers) + 1)
            except Fault, f:
                self.failIf(f.status == 304) #fail if not modified
    
    def test_if_modified_since_invalid_date(self):
        c = self.client.list_containers(if_modified_since='')
        self.assertEqual(len(c), len(self.containers))
    
    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            args = {'if_modified_since':'%s' %since.strftime(f)}
            
            #assert not modified
            self.assert_raises_fault(304, self.client.list_containers, **args)
    
    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            c = self.client.list_containers(if_unmodified_since=since.strftime(f))
            
            #assert success
            self.assertEqual(self.containers, c)
    
    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #add a new container
        self.client.create_container('dummy')
        
        for f in DATE_FORMATS:
            past = t2.strftime(f)
            
            args = {'if_unmodified_since':'%s' %past}
            
            #assert precondition failed
            self.assert_raises_fault(412, self.client.list_containers, **args)
    
class AccountPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in self.containers:
            self.client.create_container(item)
        
        #keep track of initial account groups
        self.initial_groups = self.client.retrieve_account_groups()
        
        #keep track of initial account meta
        self.initial_meta = self.client.retrieve_account_metadata(restricted=True)
        
        meta = {'foo':'bar'}
        self.client.update_account_metadata(**meta)
        self.updated_meta = self.initial_meta.update(meta)
    
    def tearDown(self):
        #delete additionally created meta
        l = []
        for m in self.client.retrieve_account_metadata(restricted=True):
            if m not in self.initial_meta:
                l.append(m)
        self.client.delete_account_metadata(l)
        
        #delete additionally created groups
        l = []
        for g in self.client.retrieve_account_groups():
            if g not in self.initial_groups:
                l.append(g)
        self.client.unset_account_groups(l)
        
        #print '#', self.client.retrieve_account_groups()
        #print '#', self.client.retrieve_account_metadata(restricted=True)
        BaseTestCase.tearDown(self)
    
    def test_update_meta(self):
        with AssertMappingInvariant(self.client.retrieve_account_groups):
            meta = {'test':'test', 'tost':'tost'}
            self.client.update_account_metadata(**meta)
            
            meta.update(self.initial_meta)
            self.assertEqual(meta,
                             self.client.retrieve_account_metadata(
                                restricted=True))
        
    def test_invalid_account_update_meta(self):
        meta = {'test':'test', 'tost':'tost'}
        self.assert_raises_fault(401,
                                 self.invalid_client.update_account_metadata,
                                 **meta)
    
    def test_reset_meta(self):
        with AssertMappingInvariant(self.client.retrieve_account_groups):
            meta = {'test':'test', 'tost':'tost'}
            self.client.update_account_metadata(**meta)
            
            meta = {'test':'test33'}
            self.client.reset_account_metadata(**meta)
            
            self.assertEqual(meta, self.client.retrieve_account_metadata(restricted=True))
    
    #def test_delete_meta(self):
    #    with AssertMappingInvariant(self.client.reset_account_groups):
    #        meta = {'test':'test', 'tost':'tost'}
    #        self.client.update_account_metadata(**meta)
    #        
    #        self.client.delete_account_metadata(**meta)
    
    def test_set_account_groups(self):
        with AssertMappingInvariant(self.client.retrieve_account_metadata):
            groups = {'pithosdev':'verigak,gtsouk,chazapis'}
            self.client.set_account_groups(**groups)
            
            self.assertEqual(groups, self.client.retrieve_account_groups())
            
            more_groups = {'clientsdev':'pkanavos,mvasilak'}
            self.client.set_account_groups(**more_groups)
            
            groups.update(more_groups)
            self.assertEqual(groups, self.client.retrieve_account_groups())
    
    def test_reset_account_groups(self):
        with AssertMappingInvariant(self.client.retrieve_account_metadata):
            groups = {'pithosdev':'verigak,gtsouk,chazapis',
                      'clientsdev':'pkanavos,mvasilak'}
            self.client.set_account_groups(**groups)
            
            self.assertEqual(groups, self.client.retrieve_account_groups())
            
            groups = {'pithosdev':'verigak,gtsouk,chazapis, papagian'}
            self.client.reset_account_groups(**groups)
            
            self.assertTrue(groups, self.client.retrieve_account_groups())
    
    def test_delete_account_groups(self):
        with AssertMappingInvariant(self.client.retrieve_account_metadata):
            groups = {'pithosdev':'verigak,gtsouk,chazapis',
                      'clientsdev':'pkanavos,mvasilak'}
            self.client.set_account_groups(**groups)
            
            self.client.unset_account_groups(groups.keys())
            
            self.assertEqual({}, self.client.retrieve_account_groups())
    
class ContainerHead(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = 'apples'
        self.client.create_container(self.container)
    
    def test_get_meta(self):
        meta = {'trash':'true'}
        t1 = datetime.datetime.utcnow()
        o = self.upload_random_data(self.container, o_names[0], **meta)
        if o:
            headers = self.client.retrieve_container_metadata(self.container)
            self.assertEqual(headers['x-container-object-count'], '1')
            self.assertEqual(headers['x-container-bytes-used'], str(len(o['data'])))
            t2 = datetime.datetime.strptime(headers['last-modified'], DATE_FORMATS[2])
            delta = (t2 - t1)
            threashold = datetime.timedelta(seconds=1) 
            self.assertTrue(delta < threashold)
            self.assertTrue(headers['x-container-object-meta'])
            self.assertTrue('Trash' in headers['x-container-object-meta'])

class ContainerGet(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = ['pears', 'apples']
        for c in self.container:
            self.client.create_container(c)
        self.obj = []
        for o in o_names[:8]:
            self.obj.append(self.upload_random_data(self.container[0], o))
        for o in o_names[8:]:
            self.obj.append(self.upload_random_data(self.container[1], o))
    
    def test_list_objects(self):
        objects = self.client.list_objects(self.container[0])
        l = [elem['name'] for elem in self.obj[:8]]
        l.sort()
        self.assertEqual(objects, l)
    
    def test_list_objects_with_limit_marker(self):
        objects = self.client.list_objects(self.container[0], limit=2)
        l = [elem['name'] for elem in self.obj[:8]]
        l.sort()
        self.assertEqual(objects, l[:2])
        
        markers = ['How To Win Friends And Influence People.pdf',
                   'moms_birthday.jpg']
        limit = 4
        for m in markers:
            objects = self.client.list_objects(self.container[0], limit=limit,
                                               marker=m)
            l = [elem['name'] for elem in self.obj[:8]]
            l.sort()
            start = l.index(m) + 1
            end = start + limit
            end = len(l) >= end and end or len(l)
            self.assertEqual(objects, l[start:end])
    
    def test_list_pseudo_hierarchical_folders(self):
        objects = self.client.list_objects(self.container[1], prefix='photos',
                                           delimiter='/')
        self.assertEquals(['photos/animals/', 'photos/me.jpg',
                           'photos/plants/'], objects)
        
        objects = self.client.list_objects(self.container[1],
                                           prefix='photos/animals',
                                           delimiter='/')
        l = ['photos/animals/cats/', 'photos/animals/dogs/']
        self.assertEquals(l, objects)
        
        objects = self.client.list_objects(self.container[1], path='photos')
        self.assertEquals(['photos/me.jpg'], objects)
    
    def test_extended_list_json(self):
        objects = self.client.list_objects(self.container[1], format='json',
                                           limit=2, prefix='photos/animals',
                                           delimiter='/')
        self.assertEqual(objects[0]['subdir'], 'photos/animals/cats/')
        self.assertEqual(objects[1]['subdir'], 'photos/animals/dogs/')
    
    def test_extended_list_xml(self):
        xml = self.client.list_objects(self.container[1], format='xml', limit=4,
                                       prefix='photos', delimiter='/')
        dirs = xml.getElementsByTagName('subdir')
        self.assertEqual(len(dirs), 2)
        self.assertEqual(dirs[0].attributes['name'].value, 'photos/animals/')
        self.assertEqual(dirs[1].attributes['name'].value, 'photos/plants/')
        
        objects = xml.getElementsByTagName('name')
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].childNodes[0].data, 'photos/me.jpg')
    
    def test_list_meta_double_matching(self):
        meta = {'quality':'aaa', 'stock':'true'}
        self.client.update_object_metadata(self.container[0],
                                           self.obj[0]['name'], **meta)
        obj = self.client.list_objects(self.container[0], meta='Quality,Stock')
        self.assertEqual(len(obj), 1)
        self.assertTrue(obj, self.obj[0]['name'])
    
    def test_list_using_meta(self):
        meta = {'quality':'aaa'}
        for o in self.obj[:2]:
            self.client.update_object_metadata(self.container[0], o['name'],
                                               **meta)
        meta = {'stock':'true'}
        for o in self.obj[3:5]:
            self.client.update_object_metadata(self.container[0], o['name'],
                                               **meta)
        
        obj = self.client.list_objects(self.container[0], meta='Quality')
        self.assertEqual(len(obj), 2)
        self.assertTrue(obj, [o['name'] for o in self.obj[:2]])
        
        # test case insensitive
        obj = self.client.list_objects(self.container[0], meta='quality')
        self.assertEqual(len(obj), 2)
        self.assertTrue(obj, [o['name'] for o in self.obj[:2]])
        
        # test multiple matches
        obj = self.client.list_objects(self.container[0], meta='Quality,Stock')
        self.assertEqual(len(obj), 4)
        self.assertTrue(obj, [o['name'] for o in self.obj[:4]])
        
        # test non 1-1 multiple match
        obj = self.client.list_objects(self.container[0], meta='Quality,aaaa')
        self.assertEqual(len(obj), 2)
        self.assertTrue(obj, [o['name'] for o in self.obj[:2]])
    
    def test_if_modified_since(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #add a new object
        self.upload_random_data(self.container[0], o_names[0])
        
        for f in DATE_FORMATS:
            past = t2.strftime(f)
            try:
                o = self.client.list_objects(self.container[0],
                                            if_modified_since=past)
                self.assertEqual(o,
                                 self.client.list_objects(self.container[0]))
            except Fault, f:
                self.failIf(f.status == 304) #fail if not modified
    
    def test_if_modified_since_invalid_date(self):
        headers = {'if-modified-since':''}
        o = self.client.list_objects(self.container[0], if_modified_since='')
        self.assertEqual(o, self.client.list_objects(self.container[0]))
    
    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            args = {'if_modified_since':'%s' %since.strftime(f)}
            
            #assert not modified
            self.assert_raises_fault(304, self.client.list_objects,
                                     self.container[0], **args)
    
    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            obj = self.client.list_objects(self.container[0],
                                           if_unmodified_since=since.strftime(f))
            
            #assert unmodified
            self.assertEqual(obj, self.client.list_objects(self.container[0]))
    
    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #add a new container
        self.client.create_container('dummy')
        
        for f in DATE_FORMATS:
            past = t2.strftime(f)
            
            args = {'if_unmodified_since':'%s' %past}
            
            #assert precondition failed
            self.assert_raises_fault(412, self.client.list_objects,
                                     self.container[0], **args)

class ContainerPut(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
    
    def test_create(self):
        self.client.create_container(self.containers[0])
        containers = self.client.list_containers()
        self.assertTrue(self.containers[0] in containers)
        self.assert_container_exists(self.containers[0])
    
    def test_create_twice(self):
        self.client.create_container(self.containers[0])
        self.assertTrue(not self.client.create_container(self.containers[0]))
    
class ContainerPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = 'apples'
        self.client.create_container(self.container)
    
    def test_update_meta(self):
        meta = {'test':'test33',
                'tost':'tost22'}
        self.client.update_container_metadata(self.container, **meta)
        headers = self.client.retrieve_container_metadata(self.container)
        for k,v in meta.items():
            k = 'x-container-meta-%s' % k
            self.assertTrue(headers[k])
            self.assertEqual(headers[k], v)

class ContainerDelete(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.client.create_container(c)
        self.upload_random_data(self.containers[1], o_names[0])
    
    def test_delete(self):
        status = self.client.delete_container(self.containers[0])[0]
        self.assertEqual(status, 204)
    
    def test_delete_non_empty(self):
        self.assert_raises_fault(409, self.client.delete_container,
                                 self.containers[1])
    
    def test_delete_invalid(self):
        self.assert_raises_fault(404, self.client.delete_container, 'c3')

class ObjectHead(BaseTestCase):
    pass

class ObjectGet(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        #create some containers
        for c in self.containers:
            self.client.create_container(c)
        
        #upload a file
        names = ('obj1', 'obj2')
        self.objects = []
        for n in names:
            self.objects.append(self.upload_random_data(self.containers[1], n))
    
    def test_get(self):
        #perform get
        o = self.client.retrieve_object(self.containers[1],
                                        self.objects[0]['name'],
                                        self.objects[0]['meta'])
        self.assertEqual(o, self.objects[0]['data'])
    
    def test_get_invalid(self):
        self.assert_raises_fault(404, self.client.retrieve_object,
                                 self.containers[0], self.objects[0]['name'])
    
    def test_get_partial(self):
        #perform get with range
        status, headers, data = self.client.request_object(self.containers[1],
                                                            self.objects[0]['name'],
                                                            range='bytes=0-499')
        
        #assert successful partial content
        self.assertEqual(status, 206)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])
        
        #assert content length
        self.assertEqual(int(headers['content-length']), 500)
        
        #assert content
        self.assertEqual(self.objects[0]['data'][:500], data)
    
    def test_get_final_500(self):
        #perform get with range
        headers = {'range':'bytes=-500'}
        status, headers, data = self.client.request_object(self.containers[1],
                                                            self.objects[0]['name'],
                                                            range='bytes=-500')
        
        #assert successful partial content
        self.assertEqual(status, 206)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])
        
        #assert content length
        self.assertEqual(int(headers['content-length']), 500)
        
        #assert content
        self.assertTrue(self.objects[0]['data'][-500:], data)
    
    def test_get_rest(self):
        #perform get with range
        offset = len(self.objects[0]['data']) - 500
        status, headers, data = self.client.request_object(self.containers[1],
                                                self.objects[0]['name'],
                                                range='bytes=%s-' %offset)
        
        #assert successful partial content
        self.assertEqual(status, 206)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])
        
        #assert content length
        self.assertEqual(int(headers['content-length']), 500)
        
        #assert content
        self.assertTrue(self.objects[0]['data'][-500:], data)
    
    def test_get_range_not_satisfiable(self):
        #perform get with range
        offset = len(self.objects[0]['data']) + 1
        
        #assert range not satisfiable
        self.assert_raises_fault(416, self.client.retrieve_object,
                                 self.containers[1], self.objects[0]['name'],
                                 range='bytes=0-%s' %offset)
    
    def test_multiple_range(self):
        #perform get with multiple range
        ranges = ['0-499', '-500', '1000-']
        bytes = 'bytes=%s' % ','.join(ranges)
        status, headers, data = self.client.request_object(self.containers[1],
                                                           self.objects[0]['name'],
                                                           range=bytes)
        
        # assert partial content
        self.assertEqual(status, 206)
        
        # assert Content-Type of the reply will be multipart/byteranges
        self.assertTrue(headers['content-type'])
        content_type_parts = headers['content-type'].split()
        self.assertEqual(content_type_parts[0], ('multipart/byteranges;'))
        
        boundary = '--%s' %content_type_parts[1].split('=')[-1:][0]
        cparts = data.split(boundary)[1:-1]
        
        # assert content parts are exactly 2
        self.assertEqual(len(cparts), len(ranges))
        
        # for each content part assert headers
        i = 0
        for cpart in cparts:
            content = cpart.split('\r\n')
            headers = content[1:3]
            content_range = headers[0].split(': ')
            self.assertEqual(content_range[0], 'Content-Range')
            
            r = ranges[i].split('-')
            if not r[0] and not r[1]:
                pass
            elif not r[0]:
                start = len(self.objects[0]['data']) - int(r[1])
                end = len(self.objects[0]['data'])
            elif not r[1]:
                start = int(r[0])
                end = len(self.objects[0]['data'])
            else:
                start = int(r[0])
                end = int(r[1]) + 1
            fdata = self.objects[0]['data'][start:end]
            sdata = '\r\n'.join(content[4:-1])
            self.assertEqual(len(fdata), len(sdata))
            self.assertEquals(fdata, sdata)
            i+=1
    
    def test_multiple_range_not_satisfiable(self):
        #perform get with multiple range
        out_of_range = len(self.objects[0]['data']) + 1
        ranges = ['0-499', '-500', '%d-' %out_of_range]
        bytes = 'bytes=%s' % ','.join(ranges)
        
        # assert partial content
        self.assert_raises_fault(416, self.client.retrieve_object,
                                 self.containers[1],
                                 self.objects[0]['name'], range=bytes)
    
    def test_get_with_if_match(self):
        #perform get with If-Match
        etag = self.objects[0]['hash']
        status, headers, data = self.client.request_object(self.containers[1],
                                                           self.objects[0]['name'],
                                                           if_match=etag)
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])
        
        #assert response content
        self.assertEqual(self.objects[0]['data'], data)
    
    def test_get_with_if_match_star(self):
        #perform get with If-Match *
        headers = {'if-match':'*'}
        status, headers, data = self.client.request_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])
        
        #assert response content
        self.assertEqual(self.objects[0]['data'], data)
    
    def test_get_with_multiple_if_match(self):
        #perform get with If-Match
        etags = [i['hash'] for i in self.objects if i]
        etags = ','.join('"%s"' % etag for etag in etags)
        status, headers, data = self.client.request_object(self.containers[1],
                                                           self.objects[0]['name'],
                                                           if_match=etags)
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])
        
        #assert response content
        self.assertEqual(self.objects[0]['data'], data)
    
    def test_if_match_precondition_failed(self):
        #assert precondition failed
        self.assert_raises_fault(412, self.client.retrieve_object,
                                 self.containers[1],
                                 self.objects[0]['name'], if_match='123')
    
    def test_if_none_match(self):
        #perform get with If-None-Match
        status, headers, data = self.client.request_object(self.containers[1],
                                                           self.objects[0]['name'],
                                                           if_none_match='123')
        
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content_type'],
                         self.objects[0]['meta']['content_type'])
    
    def test_if_none_match(self):
        #perform get with If-None-Match * and assert not modified
        self.assert_raises_fault(304, self.client.retrieve_object,
                                 self.containers[1],
                                 self.objects[0]['name'],
                                 if_none_match='*')
    
    def test_if_none_match_not_modified(self):
        #perform get with If-None-Match and assert not modified
        self.assert_raises_fault(304, self.client.retrieve_object,
                                 self.containers[1],
                                 self.objects[0]['name'],
                                 if_none_match=self.objects[0]['hash'])
        
        meta = self.client.retrieve_object_metadata(self.containers[1],
                                                    self.objects[0]['name'])
        self.assertEqual(meta['etag'], self.objects[0]['hash'])
    
    def test_if_modified_since(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #modify the object
        self.upload_data(self.containers[1],
                           self.objects[0]['name'],
                           self.objects[0]['data'][:200])
        
        for f in DATE_FORMATS:
            past = t2.strftime(f)
            
            headers = {'if-modified-since':'%s' %past}
            try:
                o = self.client.retrieve_object(self.containers[1],
                                                self.objects[0]['name'],
                                                if_modified_since=past)
                self.assertEqual(o,
                                 self.client.retrieve_object(self.containers[1],
                                                             self.objects[0]['name']))
            except Fault, f:
                self.failIf(f.status == 304)
    
    def test_if_modified_since_invalid_date(self):
        o = self.client.retrieve_object(self.containers[1],
                                        self.objects[0]['name'],
                                        if_modified_since='')
        self.assertEqual(o, self.client.retrieve_object(self.containers[1],
                                                        self.objects[0]['name']))
            
    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            #assert not modified
            self.assert_raises_fault(304, self.client.retrieve_object,
                                     self.containers[1], self.objects[0]['name'],
                                     if_modified_since=since.strftime(f))
    
    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            t = since.strftime(f)
            status, headers, data = self.client.request_object(self.containers[1],
                                                               self.objects[0]['name'],
                                                               if_unmodified_since=t)
            #assert success
            self.assertEqual(status, 200)
            self.assertEqual(self.objects[0]['data'], data)
            
            #assert content-type
            self.assertEqual(headers['content-type'],
                             self.objects[0]['meta']['content_type'])
    
    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #modify the object
        self.upload_data(self.containers[1],
                           self.objects[0]['name'],
                           self.objects[0]['data'][:200])
        
        for f in DATE_FORMATS:
            past = t2.strftime(f)
            #assert precondition failed
            self.assert_raises_fault(412, self.client.retrieve_object,
                                     self.containers[1], self.objects[0]['name'],
                                     if_unmodified_since=past)
    
    def test_hashes(self):
        l = 8388609
        fname = 'largefile'
        o = self.upload_random_data(self.containers[1], fname, l)
        if o:
            data = self.client.retrieve_object(self.containers[1], fname,
                                               format='json')
            body = json.loads(data)
            hashes = body['hashes']
            block_size = body['block_size']
            block_hash = body['block_hash']
            block_num = l/block_size == 0 and l/block_size or l/block_size + 1
            self.assertTrue(len(hashes), block_num)
            i = 0
            for h in hashes:
                start = i * block_size
                end = (i + 1) * block_size
                hash = compute_block_hash(o['data'][start:end], block_hash)
                self.assertEqual(h, hash)
                i += 1

class ObjectPut(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = 'c1'
        self.client.create_container(self.container)
    
    def test_upload(self):
        name = o_names[0]
        meta = {'test':'test1'}
        o = self.upload_random_data(self.container, name, **meta)
        
        headers = self.client.retrieve_object_metadata(self.container,
                                                       name,
                                                       restricted=True)
        self.assertTrue('test' in headers.keys())
        self.assertEqual(headers['test'], meta['test'])
        
        #assert uploaded content
        status, h, data = self.client.request_object(self.container, name)
        self.assertEqual(len(o['data']), int(h['content-length']))
        self.assertEqual(o['data'], data)
        
        #assert content-type
        self.assertEqual(h['content-type'], o['meta']['content_type'])
    
    def test_upload_unprocessable_entity(self):
        meta={'etag':'123', 'test':'test1'}
        
        #assert unprocessable entity
        self.assert_raises_fault(422, self.upload_random_data, self.container,
                                 o_names[0], **meta)
    
    def test_chunked_transfer(self):
        data = get_random_data()
        objname = 'object'
        self.client.create_object_using_chunks(self.container, objname,
                                               StringIO(data))
        
        uploaded_data = self.client.retrieve_object(self.container, objname)
        self.assertEqual(data, uploaded_data)

class ObjectCopy(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.client.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])
    
    def test_copy(self):
        with AssertMappingInvariant(self.client.retrieve_object_metadata,
                             self.containers[0], self.obj['name']):
            #perform copy
            meta = {'test':'testcopy'}
            status = self.client.copy_object(self.containers[0],
                                              self.obj['name'],
                                              self.containers[0],
                                              'testcopy',
                                              **meta)[0]
            
            #assert copy success
            self.assertEqual(status, 201)
            
            #assert access the new object
            headers = self.client.retrieve_object_metadata(self.containers[0],
                                                           'testcopy')
            self.assertTrue('x-object-meta-test' in headers.keys())
            self.assertTrue(headers['x-object-meta-test'], 'testcopy')
            
            #assert etag is the same
            self.assertEqual(headers['etag'], self.obj['hash'])
            
            #assert src object still exists
            self.assert_object_exists(self.containers[0], self.obj['name'])
    
    def test_copy_from_different_container(self):
        with AssertMappingInvariant(self.client.retrieve_object_metadata,
                             self.containers[0], self.obj['name']):
            meta = {'test':'testcopy'}
            status = self.client.copy_object(self.containers[0],
                                             self.obj['name'],
                                             self.containers[1],
                                             'testcopy',
                                             **meta)[0]
            self.assertEqual(status, 201)
            
            # assert updated metadata
            meta = self.client.retrieve_object_metadata(self.containers[1],
                                                           'testcopy',
                                                           restricted=True)
            self.assertTrue('test' in meta.keys())
            self.assertTrue(meta['test'], 'testcopy')
            
            #assert src object still exists
            self.assert_object_exists(self.containers[0], self.obj['name'])
    
    def test_copy_invalid(self):
        #copy from invalid object
        meta = {'test':'testcopy'}
        self.assert_raises_fault(404, self.client.copy_object, self.containers[0],
                                 'test.py', self.containers[1], 'testcopy',
                                 **meta)
        
        #copy from invalid container
        meta = {'test':'testcopy'}
        self.assert_raises_fault(404, self.client.copy_object, self.containers[1],
                                 self.obj['name'], self.containers[1],
                                 'testcopy', **meta)
        

class ObjectMove(ObjectCopy):
    def test_move(self):
        #perform move
        meta = {'test':'testcopy'}
        src_path = os.path.join('/', self.containers[0], self.obj['name'])
        status = self.client.move_object(self.containers[0], self.obj['name'],
                                         self.containers[0], 'testcopy',
                                         **meta)[0]
        
        #assert successful move
        self.assertEqual(status, 201)
        
        #assert updated metadata
        meta = self.client.retrieve_object_metadata(self.containers[0],
                                                    'testcopy',
                                                    restricted=True)
        self.assertTrue('test' in meta.keys())
        self.assertTrue(meta['test'], 'testcopy')
        
        #assert src object no more exists
        self.assert_object_not_exists(self.containers[0], self.obj['name'])

class ObjectPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.client.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])
    
    def test_update_meta(self):
        #perform update metadata
        more = {'foo':'foo', 'bar':'bar'}
        status = self.client.update_object_metadata(self.containers[0],
                                                    self.obj['name'],
                                                    **more)[0]
        #assert request accepted
        self.assertEqual(status, 202)
        
        #assert old metadata are still there
        headers = self.client.retrieve_object_metadata(self.containers[0],
                                                       self.obj['name'],
                                                       restricted=True)
        #assert new metadata have been updated
        for k,v in more.items():
            self.assertTrue(k in headers.keys())
            self.assertTrue(headers[k], v)
    
    def test_update_object(self,
                           first_byte_pos=0,
                           last_byte_pos=499,
                           instance_length = True,
                           content_length = 500):
        l = len(self.obj['data'])
        length = l if instance_length else '*'
        range = 'bytes %d-%d/%s' %(first_byte_pos,
                                       last_byte_pos,
                                       length)
        partial = last_byte_pos - first_byte_pos + 1
        data = get_random_data(partial)
        args = {'content_type':'application/octet-stream',
                'content_range':'%s' %range}
        if content_length:
            args['content_length'] = content_length
        
        status = self.client.update_object(self.containers[0], self.obj['name'],
                                  StringIO(data), **args)[0]
        
        if partial < 0 or (instance_length and l <= last_byte_pos):
            self.assertEqual(status, 202)    
        else:
            self.assertEqual(status, 204)           
            #check modified object
            content = self.client.retrieve_object(self.containers[0],
                                              self.obj['name'])
            self.assertEqual(content[0:partial], data)
            self.assertEqual(content[partial:l], self.obj['data'][partial:l])
    
    def test_update_object_no_content_length(self):
        self.test_update_object(content_length = None)
    
    def test_update_object_invalid_content_length(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj['name']):
            self.assert_raises_fault(400, self.test_update_object,
                                     content_length = 1000)
    
    def test_update_object_invalid_range(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj['name']):
            self.assert_raises_fault(416, self.test_update_object, 499, 0, True)
    
    def test_update_object_invalid_range_and_length(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj['name']):
            self.assert_raises_fault(416, self.test_update_object, 499, 0, True,
                                     -1)
    
    def test_update_object_invalid_range_with_no_content_length(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj['name']):
            self.assert_raises_fault(416, self.test_update_object, 499, 0, True,
                                     content_length = None)
    
    def test_update_object_out_of_limits(self):    
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj['name']):
            l = len(self.obj['data'])
            self.assert_raises_fault(416, self.test_update_object, 0, l+1, True)
    
    def test_append(self):
        data = get_random_data(500)
        headers = {}
        self.client.update_object(self.containers[0], self.obj['name'],
                                  StringIO(data), content_length=500,
                                  content_type='application/octet-stream')
        
        content = self.client.retrieve_object(self.containers[0],
                                              self.obj['name'])
        self.assertEqual(len(content), len(self.obj['data']) + 500)
        self.assertEqual(content[:-500], self.obj['data'])
    
    def test_update_with_chunked_transfer(self):
        data = get_random_data(500)
        dl = len(data)
        fl = len(self.obj['data'])
        
        self.client.update_object_using_chunks(self.containers[0],
                                               self.obj['name'], StringIO(data),
                                               offset=0,
                                               content_type='application/octet-stream')
        
        #check modified object
        content = self.client.retrieve_object(self.containers[0],
                                              self.obj['name'])
        self.assertEqual(content[0:dl], data)
        self.assertEqual(content[dl:fl], self.obj['data'][dl:fl])

class ObjectDelete(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.client.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])
    
    def test_delete(self):
        #perform delete object
        self.client.delete_object(self.containers[0], self.obj['name'])[0]
    
    def test_delete_invalid(self):
        #assert item not found
        self.assert_raises_fault(404, self.client.delete_object, self.containers[1],
                                 self.obj['name'])

class AssertMappingInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
    
    def __enter__(self):
        self.map = self.callable(*self.args, **self.kwargs)
        return self.map
    
    def __exit__(self, type, value, tb):
        map = self.callable(*self.args, **self.kwargs)
        for k in self.map.keys():
            if is_date(self.map[k]):
                continue
            assert map[k] == self.map[k]

class AssertContentInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
    
    def __enter__(self):
        self.content = self.callable(*self.args, **self.kwargs)[2]
        return self.content
    
    def __exit__(self, type, value, tb):
        content = self.callable(*self.args, **self.kwargs)[2]
        assert self.content == content

def get_content_splitted(response):
    if response:
        return response.content.split('\n')

def compute_md5_hash(data):
    md5 = hashlib.md5()
    offset = 0
    md5.update(data)
    return md5.hexdigest().lower()

def compute_block_hash(data, algorithm):
    h = hashlib.new(algorithm)
    h.update(data.rstrip('\x00'))
    return h.hexdigest()

def get_random_data(length=500):
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.choice(char_set) for x in range(length))

def is_date(date):
    MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()
    __D = r'(?P<day>\d{2})'
    __D2 = r'(?P<day>[ \d]\d)'
    __M = r'(?P<mon>\w{3})'
    __Y = r'(?P<year>\d{4})'
    __Y2 = r'(?P<year>\d{2})'
    __T = r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})'
    RFC1123_DATE = re.compile(r'^\w{3}, %s %s %s %s GMT$' % (__D, __M, __Y, __T))
    RFC850_DATE = re.compile(r'^\w{6,9}, %s-%s-%s %s GMT$' % (__D, __M, __Y2, __T))
    ASCTIME_DATE = re.compile(r'^\w{3} %s %s %s %s$' % (__M, __D2, __T, __Y))
    for regex in RFC1123_DATE, RFC850_DATE, ASCTIME_DATE:
        m = regex.match(date)
        if m is not None:
            return True
    return False

o_names = ['kate.jpg',
           'kate_beckinsale.jpg',
           'How To Win Friends And Influence People.pdf',
           'moms_birthday.jpg',
           'poodle_strut.mov',
           'Disturbed - Down With The Sickness.mp3',
           'army_of_darkness.avi',
           'the_mad.avi',
           'photos/animals/dogs/poodle.jpg',
           'photos/animals/dogs/terrier.jpg',
           'photos/animals/cats/persian.jpg',
           'photos/animals/cats/siamese.jpg',
           'photos/plants/fern.jpg',
           'photos/plants/rose.jpg',
           'photos/me.jpg']

if __name__ == "__main__":
    unittest.main()