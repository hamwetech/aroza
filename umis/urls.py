"""umis URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import url, include
from django.contrib import admin
from conf import urls as conf_urls
from userprofile import urls as profile_urls
from product import urls as product_urls
from coop import urls as coop_urls 
from partner import urls as partner_urls
from operations import urls as op_urls
from endpoint import urls as ep_urls
from messaging import urls as msg_urls
from activity import urls as act_urls
from payment import urls as pay_urls
from credit import urls as credit_urls
from account import urls as account_urls

from dashboard.views import DashboardView
from userprofile.views.authentication import LoginView, LogoutView
from conf.views import Handle404, Handle403

handler404 = Handle404.as_view()
handler403 = Handle403.as_view()

urlpatterns = [
    # url(r'^admin/', admin.site.urls),
    url(r'^conf/', include(conf_urls, namespace='conf')),
    url(r'^profile/', include(profile_urls, namespace='profile')),
    url(r'^product/', include(product_urls, namespace='product')),
    url(r'^payment/', include(pay_urls, namespace='payment')),
    url(r'^coop/', include(coop_urls, namespace='coop')),
    url(r'^op/', include(op_urls, namespace='op')),
    url(r'^partner/', include(partner_urls, namespace='partner')),
    url(r'^endpoint/', include(ep_urls, namespace='endpoint')),
    url(r'^messaging/', include(msg_urls, namespace='messaging')),
    url(r'^activity/', include(act_urls, namespace='activity')),
    url(r'^credit/', include(credit_urls, namespace='credit')),
    url(r'^account/', include(account_urls, namespace='account')),
    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),
    url(r'^$', DashboardView.as_view(), name='dashboard'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
