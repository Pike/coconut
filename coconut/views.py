# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is coconut.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''
'''

from django.shortcuts import render_to_response

from dmstatus.models import Sourcestamp, Change, Source_Changes, Build

try:
    import json
except:
    import simplejson as json
from datetime import datetime
now = datetime(2010, 8, 31, 13, 0, 0)

def index(request):
    return render_to_response('coconut/index.html', {})


def sources(request):
    count = int(request.GET.get('count', 50))
    _sources = Sourcestamp.objects.order_by('-pk')
    if 'offset' in request.GET:
         _sources = _sources.filter(id__lt = int(request.GET['offset']))
    if 'exclude_empty' in request.GET:
        _sources = _sources.exclude(builds__isnull=True)
        _sources = _sources.exclude(changes__isnull=True)
    _sources = _sources[:count]
    return render_to_response('coconut/sources.html',
                              {
                                  'sources':_sources,
                                  'next':_sources[count-1].id,
                                  'offset': request.GET.get('offset', None),
                                  'count':count,
                                  'exclude_empty': 'exclude_empty' in request.GET
                               })


def source(request, revision):
    _sources = Sourcestamp.objects.filter(revision=revision).order_by('-pk')
    return render_to_response('coconut/source.html',
                              {
                                  'sources': _sources,
                                  'revision': revision
                               })


def changes(request):
    count = int(request.GET.get('count', 50))
    _changes = Change.objects.order_by('-pk')
    if 'offset' in request.GET:
         _changes = _changes.filter(id__lt = int(request.GET.get('offset')))
    _changes = list(_changes[:count].values_list('id', flat=True))
    _scs = Source_Changes.objects.filter(change__in=_changes)
    _scs = _scs.order_by('-change__id')
    chunks = []
    cid = None
    chunk = None
    for sc in _scs:
        if sc.change.id != cid:
            chunk = {'change':sc.change,'builds':[]}
            chunks.append(chunk)
            cid = sc.change.id
        chunk['builds'] += sc.source.builds.all()

    return render_to_response('coconut/changes.html',
                              {
                                  'chunks':chunks,
                                  'next': max(_changes),
                                  'count':count
                               })


stati = ['success','warning','fail','exception']
def build(request, id):
    """Show info about a particular build.

    Lot's of bold assumptions here, given that we're just historic
    data. Also, timedelta to seconds conversion should be better.
    """
    b = Build.objects.get(id = int(id))
    steps_q = b.steps.order_by('order')
    fulltime = (b.endtime - b.starttime).seconds*0.01
    def mangle(s):
        d = s.__dict__.copy()
        if s.starttime is not None:
            d['offset'] = (s.starttime - b.starttime).seconds/fulltime
            d['duration'] = (s.endtime - s.starttime).seconds
            d['width'] = d['duration']/fulltime
        d['description'] = json.loads(s.description)
        d['class'] = s.status is not None and stati[s.status] or "future"
        return d
    steps = map(mangle, steps_q)
    def prop2dict(p):
        pv = p.value
        return {'name': p.name,
                'source': p.source,
                'value': p.value is not None and json.loads(p.value) or None}
    properties = map(prop2dict, b.properties.all())
    return render_to_response('coconut/build.html',
                              {
                                  'build': b,
                                  'steps': steps,
                                  'duration': (b.endtime-b.starttime).seconds,
                                  'properties': properties
                                  })
