from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from Guest.models import Register
from Shop.models import Product, Category, Brand

from .models import Profile, Cart, CartItem, Order, OrderItem


# =========================================================
# HELPER
# =========================================================

def validate_positive_id(value):
    """
    Safely convert an ID value into a positive integer.
    Returns None if the value is invalid.
    """

    try:
        value = int(value)

        if value <= 0:
            return None

        return value

    except (TypeError, ValueError):
        return None


# =========================================================
# USER HOME
# =========================================================

@login_required
def home(request):

    user = request.current_user

    categories = (
        Category.objects
        .all()
        .order_by("name")
    )

    brands = (
        Brand.objects
        .all()
        .order_by("name")
    )

    products = (
        Product.objects
        .select_related(
            "shop",
            "category",
            "brand",
        )
        .all()
        .order_by("-created_at")
    )

    return render(
        request,
        "User/home.html",
        {
            "user": user,
            "user_name": user.name,
            "categories": categories,
            "brands": brands,
            "products": products,
        }
    )


# =========================================================
# PRODUCTS
# =========================================================

@login_required
def products(request):

    user = request.current_user

    # -----------------------------------------------------
    # CATEGORIES
    # -----------------------------------------------------

    categories = (
        Category.objects
        .all()
        .order_by("name")
    )

    # -----------------------------------------------------
    # BRANDS
    # -----------------------------------------------------

    brands = (
        Brand.objects
        .all()
        .order_by("name")
    )

    # -----------------------------------------------------
    # ALL PRODUCTS
    #
    # IMPORTANT:
    # Start with every Product object.
    # Do NOT filter by image.
    # Do NOT filter by shop approval.
    # Do NOT filter by user.
    # -----------------------------------------------------

    product_list = (
        Product.objects
        .select_related(
            "shop",
            "category",
            "brand",
        )
        .all()
        .order_by("-created_at")
    )

    # -----------------------------------------------------
    # FILTER VALUES
    # -----------------------------------------------------

    category_id = request.GET.get(
        "category",
        ""
    ).strip()

    brand_id = request.GET.get(
        "brand",
        ""
    ).strip()

    selected_category = None
    selected_brand = None

    # -----------------------------------------------------
    # CATEGORY FILTER
    # -----------------------------------------------------

    if category_id:

        category_pk = validate_positive_id(
            category_id
        )

        if category_pk:

            selected_category = (
                Category.objects
                .filter(id=category_pk)
                .first()
            )

            if selected_category:

                product_list = (
                    product_list
                    .filter(
                        category_id=selected_category.id
                    )
                )

    # -----------------------------------------------------
    # BRAND FILTER
    # -----------------------------------------------------

    if brand_id:

        brand_pk = validate_positive_id(
            brand_id
        )

        if brand_pk:

            selected_brand = (
                Brand.objects
                .filter(id=brand_pk)
                .first()
            )

            if selected_brand:

                product_list = (
                    product_list
                    .filter(
                        brand_id=selected_brand.id
                    )
                )

    # -----------------------------------------------------
    # PAGE TITLE
    # -----------------------------------------------------

    if selected_category and selected_brand:

        page_title = (
            f"{selected_category.name} • "
            f"{selected_brand.name}"
        )

    elif selected_category:

        page_title = selected_category.name

    elif selected_brand:

        page_title = selected_brand.name

    else:

        page_title = "All Products"

    # -----------------------------------------------------
    # PAGE DESCRIPTION
    # -----------------------------------------------------

    if selected_category and selected_brand:

        page_description = (
            f"Showing {selected_category.name} "
            f"products from {selected_brand.name}."
        )

    elif selected_category:

        page_description = (
            f"Explore products in "
            f"{selected_category.name}."
        )

    elif selected_brand:

        page_description = (
            f"Explore products from "
            f"{selected_brand.name}."
        )

    else:

        page_description = (
            "Browse products added by our trusted shops."
        )

    # -----------------------------------------------------
    # FINAL QUERYSET
    # -----------------------------------------------------

    product_count = product_list.count()

    print("=" * 70)
    print("MINISHOP PRODUCT PAGE")
    print("=" * 70)
    print("GET parameters:", request.GET)
    print("Category:", category_id or "None")
    print("Brand:", brand_id or "None")
    print("Selected category:", selected_category)
    print("Selected brand:", selected_brand)
    print("Products found:", product_count)
    print("=" * 70)

    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------

    return render(
        request,
        "User/products.html",
        {
            "user": user,

            "products": product_list,

            "product_count": product_count,

            "categories": categories,

            "brands": brands,

            "selected_category": selected_category,

            "selected_brand": selected_brand,

            "page_title": page_title,

            "page_description": page_description,

            "category_id": category_id,

            "brand_id": brand_id,
        }
    )


# =========================================================
# PRODUCT DETAIL
# =========================================================

@login_required
def product_detail(request, pk):

    user = request.current_user

    product = get_object_or_404(
        Product.objects.select_related(
            "shop",
            "category",
            "brand",
        ),
        id=pk,
    )

    return render(
        request,
        "User/product_detail.html",
        {
            "user": user,
            "product": product,
        }
    )


# =========================================================
# PROFILE
# =========================================================

@login_required
def profile(request):

    user = request.current_user

    profile, created = Profile.objects.get_or_create(
        user=user
    )

    return render(
        request,
        "User/profile.html",
        {
            "user": user,
            "profile": profile,
        }
    )


# =========================================================
# CART
# =========================================================

@login_required
def cart(request):

    user = request.current_user

    cart, created = Cart.objects.get_or_create(
        user=user
    )

    cart_items = (
        CartItem.objects
        .filter(cart=cart)
        .select_related(
            "product",
            "product__shop",
            "product__category",
            "product__brand",
        )
    )

    total = 0

    for item in cart_items:

        total += (
            item.product.price *
            item.quantity
        )

    return render(
        request,
        "User/cart.html",
        {
            "user": user,
            "cart": cart,
            "cart_items": cart_items,
            "total": total,
        }
    )


# =========================================================
# ADD TO CART
# =========================================================

@login_required
def add_to_cart(request, product_id):

    if request.method != "POST":

        return redirect("user_products")

    user = request.current_user

    product = get_object_or_404(
        Product,
        id=product_id
    )

    cart, created = Cart.objects.get_or_create(
        user=user
    )

    quantity = request.POST.get(
        "quantity",
        "1"
    )

    try:

        quantity = int(quantity)

        if quantity < 1:
            quantity = 1

    except (TypeError, ValueError):

        quantity = 1

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={
            "quantity": quantity
        }
    )

    if not created:

        cart_item.quantity += quantity

        cart_item.save(
            update_fields=["quantity"]
        )

    messages.success(
        request,
        f"{product.name} added to your cart."
    )

    return redirect("cart")


# =========================================================
# UPDATE CART ITEM
# =========================================================

@login_required
def update_cart_item(request, item_id):

    if request.method != "POST":

        return redirect("cart")

    user = request.current_user

    cart = get_object_or_404(
        Cart,
        user=user
    )

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart=cart
    )

    quantity = request.POST.get(
        "quantity",
        "1"
    )

    try:

        quantity = int(quantity)

    except (TypeError, ValueError):

        quantity = 1

    if quantity <= 0:

        item.delete()

        messages.success(
            request,
            "Item removed from cart."
        )

    else:

        item.quantity = quantity

        item.save(
            update_fields=["quantity"]
        )

        messages.success(
            request,
            "Cart updated."
        )

    return redirect("cart")


# =========================================================
# REMOVE CART ITEM
# =========================================================

@login_required
def remove_cart_item(request, item_id):

    if request.method != "POST":

        return redirect("cart")

    user = request.current_user

    cart = get_object_or_404(
        Cart,
        user=user
    )

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart=cart
    )

    item.delete()

    messages.success(
        request,
        "Item removed from cart."
    )

    return redirect("cart")


# =========================================================
# ORDERS
# =========================================================

@login_required
def orders(request):

    user = request.current_user

    order_list = (
        Order.objects
        .filter(user=user)
        .prefetch_related(
            "items",
            "items__product",
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "User/orders.html",
        {
            "user": user,
            "orders": order_list,
        }
    )