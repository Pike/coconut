from django.conf.urls.defaults import *

urlpatterns = patterns(
    'coconut.views',
    (r'^$', 'index'),
    (r'^sources$', 'sources'),
    (r'^source/(.+)$', 'source'),
    (r'^changes$', 'changes'),
    (r'^build/(\d+)$', 'build'),
)
