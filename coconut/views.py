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

from dmstatus.models import Sourcestamp, Change, Source_Changes, Build,\
     Build_Properties, Property

try:
    import json
except:
    import simplejson as json
from collections import defaultdict
from datetime import datetime
now = datetime(2010, 8, 31, 13, 0, 0)
stati = ['success','warning','fail','skipped','exception']

def index(request):
    return render_to_response('coconut/index.html', {})


class PlatformBuilds(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, list)

def sources(request):
    count = int(request.GET.get('count', 50))
    _sources = Sourcestamp.objects.order_by('-pk')
    if 'offset' in request.GET:
         _sources = _sources.filter(id__lt = int(request.GET['offset']))
    if 'exclude_empty' in request.GET:
        _sources = _sources.exclude(builds__isnull=True)
        _sources = _sources.exclude(changes__isnull=True)
    if 'branch' in request.GET:
        _sources = _sources.filter(branch__contains=request.GET['branch'])
    if 'category' in request.GET:
        _sources = _sources.filter(builds__builder__category=request.GET['category']).distinct()
    if 'revision' in request.GET:
        _sources = _sources.filter(revision=request.GET['revision'])
    _sources = _sources[:count]
    _sources=list(_sources)
    builds = Build.objects.filter(source__in=_sources).order_by('starttime')
    if 'category' in request.GET:
        builds = builds.filter(builder__category=request.GET['category'])
    builds = list(builds.select_related('builder'))
    p2plat=dict(map(lambda t:(t[0],json.loads(t[1])),
                    Property.objects.filter(name='platform').values_list('id','value')))
    bids = map(lambda b: b.id, builds)
    bps = Build_Properties.objects.filter(build__in=bids,
                                          property__in=p2plat.keys())
    b2plat = dict(map(lambda t: (t[0],p2plat[t[1]]),
                      bps.values_list('build__id','property__id')))
    s2b = defaultdict(PlatformBuilds)
    for b in builds:
        bd = b.__dict__
        platform = b2plat.get(b.id, 'unknown')
        s2b[b.source.id][platform].append({'builder': b.builder.name,
                                 'number': b.buildnumber,
                                 'id': b.id,
                                 'platform': platform,
                                 'result': b.result is not None and stati[b.result] or "running"})
    def toList(dd):
        return [{'platform':k,'builds':dd[k]} for k in sorted(dd.keys())]
    _sources = map(lambda _s:{"s":_s, "builds":toList(s2b[_s.id])}, _sources)
    return render_to_response('coconut/sources.html',
                              {
                                  'sources':_sources,
                                  'next':_sources[-1]['s'].id,
                                  'offset': request.GET.get('offset', None),
                                  'count':count,
                                  'branches': request.GET.getlist('branch'),
                                  'revisions': request.GET.getlist('revision'),
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
        if (s.starttime is not None):
            d['duration'] = (s.endtime - s.starttime).seconds
            if fulltime:
                d['offset'] = (s.starttime - b.starttime).seconds/fulltime
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
                                  'properties': properties,
                                  'result': b.result is not None and stati[b.result] or 'running'
                                  })
