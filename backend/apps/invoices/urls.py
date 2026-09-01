from rest_framework.routers import SimpleRouter

from apps.invoices.views import InvoiceViewSet

app_name = "invoices"

router = SimpleRouter()
router.register(r"invoices", InvoiceViewSet, basename="invoice")

urlpatterns = router.urls
