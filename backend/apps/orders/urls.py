from rest_framework.routers import SimpleRouter

from apps.orders.views import OrderViewSet

app_name = "orders"

router = SimpleRouter()
router.register(r"orders", OrderViewSet, basename="order")

urlpatterns = router.urls
