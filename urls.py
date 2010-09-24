from django.conf.urls.defaults import *
from django.contrib import admin


admin.autodiscover()


urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^bookkeeping/', include('bookkeeping.api.urls')),
)


#urlpatterns += patterns('piston.authentication',
#    url(r'^oauth/request_token/$','oauth_request_token'),
#    url(r'^oauth/authorize/$','oauth_user_auth'),
#    url(r'^oauth/access_token/$','oauth_access_token'),
#)

