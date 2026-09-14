from django.urls import path

from . import views


urlpatterns = [

    # =====================================================
    # DASHBOARD
    # =====================================================

    path(
        "",
        views.home,
        name="shop_home"
    ),


    # =====================================================
    # PRODUCTS
    # =====================================================

    path(
        "products/",
        views.products,
        name="shop_products"
    ),

    path(
        "products/add/",
        views.add_product,
        name="add_product"
    ),

    path(
        "products/<int:pk>/edit/",
        views.edit_product,
        name="edit_product"
    ),

    path(
        "products/<int:pk>/delete/",
        views.delete_product,
        name="delete_product"
    ),


    # =====================================================
    # CATEGORIES
    # =====================================================

    path(
        "categories/",
        views.categories,
        name="shop_categories"
    ),

    path(
        "categories/add/",
        views.add_category,
        name="add_category"
    ),

    path(
        "categories/<int:pk>/",
        views.category_products,
        name="category_products"
    ),


    # =====================================================
    # BRANDS
    # =====================================================

    path(
        "brands/",
        views.brands,
        name="shop_brands"
    ),

    path(
        "brands/add/",
        views.add_brand,
        name="add_brand"
    ),

    path(
        "brands/<int:pk>/",
        views.brand_products,
        name="brand_products"
    ),


    # =====================================================
    # REVIEWS
    # =====================================================

    path(
        "reviews/",
        views.reviews,
        name="shop_reviews"
    ),

    path(
        "reviews/<int:review_id>/reply/",
        views.reply_review,
        name="reply_review"
    ),


    # =====================================================
    # ORDERS
    # =====================================================

    path(
        "orders/",
        views.orders,
        name="shop_orders"
    ),

    path(
        "orders/<int:order_id>/status/",
        views.update_order_status,
        name="update_order_status"
    ),


    # =====================================================
    # LOGOUT
    # =====================================================

    path(
        "logout/",
        views.logout,
        name="shop_logout"
    ),
]