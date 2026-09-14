from django.urls import path
from . import views


urlpatterns = [

    # =====================================================
    # USER HOME
    # =====================================================

    path(
        "",
        views.home,
        name="user_home"
    ),

    # =====================================================
    # PRODUCTS
    # =====================================================

    path(
        "products/",
        views.products,
        name="user_products"
    ),

    path(
        "products/<int:pk>/",
        views.product_detail,
        name="product_detail"
    ),

    path(
        "products/<int:pk>/review/",
        views.submit_review,
        name="submit_review"
    ),

    # =====================================================
    # PROFILE
    # =====================================================

    path(
        "profile/",
        views.profile,
        name="profile"
    ),

    path(
        "profile/edit/",
        views.edit_profile,
        name="edit_profile"
    ),

    # =====================================================
    # CHANGE PASSWORD
    # =====================================================

    path(
        "change-password/",
        views.change_password,
        name="change_password"
    ),

    # =====================================================
    # CART
    # =====================================================

    path(
        "cart/",
        views.cart,
        name="cart"
    ),

    path(
        "cart/add/<int:pk>/",
        views.add_to_cart,
        name="add_to_cart"
    ),

    path(
        "cart/update/<int:item_id>/",
        views.update_cart,
        name="update_cart"
    ),

    path(
        "cart/remove/<int:item_id>/",
        views.remove_from_cart,
        name="remove_from_cart"
    ),

    # =====================================================
    # CHECKOUT
    # =====================================================

    path(
        "checkout/",
        views.checkout,
        name="checkout"
    ),

    path(
        "checkout/place-order/",
        views.place_order,
        name="place_order"
    ),

    # =====================================================
    # ORDER
    # =====================================================

    path(
        "order-success/<int:pk>/",
        views.order_success,
        name="order_success"
    ),

    path(
        "orders/",
        views.orders,
        name="orders"
    ),

    # =====================================================
    # LOGOUT
    # =====================================================

    path(
        "logout/",
        views.logout,
        name="user_logout"
    ),

]