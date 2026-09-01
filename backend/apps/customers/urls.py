from rest_framework.routers import SimpleRouter

from apps.customers.views import CustomerViewSet

app_name = "customers"

router = SimpleRouter()
router.register(r"customers", CustomerViewSet, basename="customer")

urlpatterns = router.urls
