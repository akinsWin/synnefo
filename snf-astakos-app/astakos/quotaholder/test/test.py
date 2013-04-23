# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from config import QHTestCase, run_test_case
from django.db import transaction

import astakos.quotaholder.callpoint as qh
from astakos.quotaholder.exception import (
    InvalidDataError,
    NoCommissionError,
    NoQuantityError,
    NoCapacityError,
    NoHoldingError,
    DuplicateError)


class QHAPITest(QHTestCase):

    @classmethod
    def setUpClass(self):
        QHTestCase.setUpClass()
        self.client = 'service_name'
        self.holder = 'h0'
        self.source = 'system'
        self.resource1 = 'r1'
        self.resource2 = 'r2'
        self.limit1 = 10
        self.limit2 = 20

    @transaction.commit_on_success
    def test_010_get_set_quota(self):
        e = 'uuid1'
        resource = 'r1'
        source = 'system'
        limit = 1
        limit1 = 2
        qh.set_quota([((e, source, resource), limit),
                      ((e, source, resource), limit1)])

        resource2 = 'r2'
        r = qh.get_quota(holders=[e], sources=[source],
                         resources=[resource, resource2])
        self.assertEqual(r, {(e, source, resource): (limit1, 0, 0)})

        r = qh.get_quota()
        self.assertEqual(r, {(e, source, resource): (limit1, 0, 0)})

    @transaction.commit_on_success
    def issue_commission(self, provisions, name=None, force=False):
        return qh.issue_commission(clientkey=self.client,
                                   name=name,
                                   force=force,
                                   provisions=provisions)

    @transaction.commit_on_success
    def test_020_commissions(self):
        holder = self.holder
        source = self.source
        resource1 = self.resource1
        resource2 = self.resource2
        limit1 = self.limit1
        limit2 = self.limit2

        qh.set_quota([((holder, source, resource1), limit1),
                      ((holder, source, resource2), limit2)])

        s1 = self.issue_commission([((holder, source, resource1), limit1/2),
                                    ((holder, source, resource2), limit2)],
                                   name="initial")
        self.assertGreater(s1, 0)

        r = qh.get_commission(self.client, s1)
        provisions = [
            {'holder': holder,
             'source': source,
             'resource': resource1,
             'quantity': limit1/2,
             },
            {'holder': holder,
             'source': source,
             'resource': resource2,
             'quantity': limit2,
             }
        ]
        self.assertEqual(r['serial'], s1)
        ps = r['provisions']
        for p in ps:
            self.assertIn(p, provisions)

        with self.assertRaises(NoCommissionError):
            qh.get_commission(self.client, s1+1)

    @transaction.commit_on_success
    def test_030_commissions_exceptions(self):
        holder = self.holder
        source = self.source
        resource1 = self.resource1
        resource2 = self.resource2
        limit1 = self.limit1
        limit2 = self.limit2

        with self.assertRaises(NoCapacityError) as cm:
            self.issue_commission([((holder, source, resource1), 1),
                                   ((holder, source, resource2), 1)])

        e = cm.exception
        provision = e.data['provision']
        self.assertEqual(provision['holder'], holder)
        self.assertEqual(provision['source'], source)
        self.assertEqual(provision['resource'], resource2)
        self.assertEqual(provision['quantity'], 1)
        self.assertEqual(e.data['usage'], limit2)
        self.assertEqual(e.data['limit'], limit2)

        with self.assertRaises(NoQuantityError) as cm:
            self.issue_commission([((holder, source, resource1), -1)])

        e = cm.exception
        provision = e.data['provision']
        self.assertEqual(provision['holder'], holder)
        self.assertEqual(provision['source'], source)
        self.assertEqual(provision['resource'], resource1)
        self.assertEqual(provision['quantity'], -1)
        self.assertEqual(e.data['available'], 0)

        with self.assertRaises(NoHoldingError) as cm:
            self.issue_commission([((holder, source, resource1), 1),
                                   (('nonex', source, resource1), 1)])

        e = cm.exception
        provision = e.data['provision']
        self.assertEqual(provision['holder'], 'nonex')
        self.assertEqual(provision['source'], source)
        self.assertEqual(provision['resource'], resource1)
        self.assertEqual(provision['quantity'], 1)

        with self.assertRaises(DuplicateError) as cm:
            self.issue_commission([((holder, source, resource1), 1),
                                   ((holder, source, resource1), 2)])

        e = cm.exception
        provision = e.data['provision']
        self.assertEqual(provision['holder'], holder)
        self.assertEqual(provision['source'], source)
        self.assertEqual(provision['resource'], resource1)
        self.assertEqual(provision['quantity'], 2)

        with self.assertRaises(InvalidDataError):
            self.issue_commission([((holder, source, resource1), 1),
                                   ((holder, source, resource1), "nan")])

        r = qh.get_quota(holders=[holder])
        quotas = {(holder, source, resource1): (limit1, 0, limit1/2),
                  (holder, source, resource2): (limit2, 0, limit2),
                  }
        self.assertEqual(r, quotas)

    @transaction.commit_on_success
    def test_040_resolve_commission(self):
        holder = self.holder
        source = self.source
        resource1 = self.resource1
        resource2 = self.resource2
        limit1 = self.limit1
        limit2 = self.limit2

        r = qh.get_pending_commissions(clientkey=self.client)
        self.assertEqual(len(r), 1)
        serial = r[0]
        r = qh.resolve_pending_commission(self.client, serial)
        self.assertEqual(r, True)
        r = qh.get_pending_commissions(clientkey=self.client)
        self.assertEqual(r, [])
        r = qh.resolve_pending_commission(self.client, serial)
        self.assertEqual(r, False)

        r = qh.get_quota(holders=[holder])
        quotas = {(holder, source, resource1): (limit1, limit1/2, limit1/2),
                  (holder, source, resource2): (limit2, limit2, limit2),
                  }
        self.assertEqual(r, quotas)

    @transaction.commit_on_success
    def test_050_resolve_commissions(self):
        holder = self.holder
        source = self.source
        resource1 = self.resource1
        resource2 = self.resource2
        limit1 = self.limit1
        limit2 = self.limit2

        serial = self.issue_commission([((holder, source, resource1), 1),
                                        ((holder, source, resource2), -1)])

        r = qh.get_quota(holders=[holder])
        quotas = {(holder, source, resource1): (limit1, limit1/2, limit1/2+1),
                  (holder, source, resource2): (limit2, limit2-1, limit2),
                  }
        self.assertEqual(r, quotas)

        r = qh.resolve_pending_commission(self.client, serial, accept=False)
        self.assertEqual(r, True)

        serial1 = self.issue_commission([((holder, source, resource1), 1),
                                         ((holder, source, resource2), -1)])

        serial2 = self.issue_commission([((holder, source, resource1), 1),
                                         ((holder, source, resource2), -1)])

        serial3 = self.issue_commission([((holder, source, resource1), 1),
                                         ((holder, source, resource2), -1)])

        r = qh.resolve_pending_commissions(clientkey=self.client,
                                           accept_set=[serial1, serial2, 0],
                                           reject_set=[serial2, serial3])
        self.assertEqual(r, ([serial1], [serial3], [0], [serial2]))

        r = qh.get_pending_commissions(clientkey=self.client)
        self.assertEqual(r, [serial2])

    @transaction.commit_on_success
    def test_060_forced_commission(self):
        holder = self.holder
        source = self.source
        resource1 = self.resource1
        resource2 = self.resource2
        limit1 = self.limit1
        limit2 = self.limit2

        r = qh.get_quota(holders=[holder])
        quotas = {
            (holder, source, resource1): (limit1, limit1/2+1, limit1/2+2),
            (holder, source, resource2): (limit2, limit2-2, limit2-1),
        }
        self.assertEqual(r, quotas)

        with self.assertRaises(NoCapacityError):
            self.issue_commission(
                [((holder, source, resource1), limit1/2+1)])

        serial = self.issue_commission(
            [((holder, source, resource1), limit1/2+1)],
            force=True)

        r = qh.resolve_pending_commission(self.client, serial, accept=True)
        self.assertEqual(r, True)

        r = qh.get_quota(holders=[holder])
        quotas = {
            (holder, source, resource1): (limit1, limit1+2, limit1+3),
            (holder, source, resource2): (limit2, limit2-2, limit2-1),
        }
        self.assertEqual(r, quotas)

    @transaction.commit_on_success
    def test_070_release_off_upper_limit(self):
        holder = self.holder
        source = self.source
        resource1 = self.resource1
        resource2 = self.resource2
        limit1 = self.limit1
        limit2 = self.limit2

        serial = self.issue_commission([((holder, source, resource1), -1)])
        r = qh.resolve_pending_commission(self.client, serial)
        self.assertEqual(r, True)

        r = qh.get_quota(holders=[holder], resources=[resource1])
        quotas = {
            (holder, source, resource1): (limit1, limit1+1, limit1+2),
        }
        self.assertEqual(r, quotas)

    @transaction.commit_on_success
    def test_080_add_resource_limit(self):
        holder = self.holder
        source = self.source
        resource1 = self.resource1
        resource2 = self.resource2
        limit1 = self.limit1
        limit2 = self.limit2

        qh.add_resource_limit(sources=[source], resources=[resource1], diff=1)
        r = qh.get_quota(holders=[holder])
        quotas = {
            (holder, source, resource1): (limit1+1, limit1+1, limit1+2),
            (holder, source, resource2): (limit2, limit2-2, limit2-1),
        }
        self.assertEqual(r, quotas)

        qh.add_resource_limit(holders=[holder, "nonex"], diff=10)
        r = qh.get_quota(holders=[holder, "nonex"])
        quotas = {
            (holder, source, resource1): (limit1+11, limit1+1, limit1+2),
            (holder, source, resource2): (limit2+10, limit2-2, limit2-1),
        }
        self.assertEqual(r, quotas)


if __name__ == "__main__":
    run_test_case(QHAPITest)
