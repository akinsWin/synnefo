# Copyright 2012 GRNET S.A. All rights reserved.
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

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.views.generic.create_update import lookup_object
from django.http import Http404

from astakos.im.models import (
    ProjectApplication, Project)

@transaction.commit_on_success
class Command(BaseCommand):
    args = "<project id>"
    help = "Update project state"

    option_list = BaseCommand.option_list + (
        make_option('--terminate',
                    action='store_true',
                    dest='terminate',
                    default=False,
                    help="Terminate group"),
        make_option('--suspend',
                    action='store_true',
                    dest='suspend',
                    default=False,
                    help="Suspend group")
    )

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please provide a group identifier")
        
        try:
            id = int(args[0])
        except ValueError:
            raise CommandError('Invalid id')
        else:
            try:
                # Is it a project id?
                p = lookup_object(Project, id, None, None)
            except Http404:
                raise CommandError('Invalid id')
            else:
                try:
                    if options['terminate']:
                        p.terminate()
                    elif options['suspend']:
                        p.suspend()
                except BaseException, e:
                    raise CommandError(e)
