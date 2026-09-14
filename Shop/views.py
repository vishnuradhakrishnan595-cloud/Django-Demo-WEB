from decimal import Decimal, InvalidOperation
from functools import wraps
import re

from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from Guest.models import Register

from User.models import (
    Order,
    OrderItem
)

from .models import (
    Product,
    Category,
    Brand,
    Review
)


# =========================================================
# CONSTANTS
# =========================================================

SESSION_TIMEOUT = 7200

MAX_PRODUCT_NAME_LENGTH = 150
MAX_DESCRIPTION_LENGTH = 2000

MAX_CATEGORY_NAME_LENGTH = 100
MAX_CATEGORY_DESCRIPTION_LENGTH = 1000

MAX_BRAND_NAME_LENGTH = 100
MAX_BRAND_DESCRIPTION_LENGTH = 1000

MAX_REVIEW_REPLY_LENGTH = 1000

MAX_PRICE = Decimal("99999999.99")


# =========================================================
# VALIDATION HELPERS
# =========================================================

def validate_text(
    value,
    min_length=2,
    max_length=100
):
    """
    General text validation.
    """

    if not value:
        return False

    value = value.strip()

    if len(value) < min_length:
        return False

    if len(value) > max_length:
        return False

    return True


# =========================================================
# NAME VALIDATION
# =========================================================

def validate_name(
    value,
    max_length=100
):
    """
    Validate names such as:

    Casio
    G-Shock
    Men's Watches
    Apple
    Nike
    """

    if not value:
        return False

    value = value.strip()

    if len(value) < 2:
        return False

    if len(value) > max_length:
        return False

    # Allows:
    # Letters
    # Numbers
    # Spaces
    # .
    # ,
    # '
    # &
    # ( )
    # -
    # +
    pattern = r"^[A-Za-z0-9À-ÿ .,'&()+-]+$"

    return bool(
        re.fullmatch(
            pattern,
            value
        )
    )


# =========================================================
# DESCRIPTION VALIDATION
# =========================================================

def validate_description(
    value,
    max_length=2000
):
    """
    Validate product/category/brand description.
    """

    if not value:
        return False

    value = value.strip()

    if len(value) > max_length:
        return False

    return True


# =========================================================
# PRICE VALIDATION
# =========================================================

def validate_price(value):
    """
    Convert and validate product price.

    Returns:
        Decimal price
        None if invalid
    """

    if not value:
        return None

    try:
        price = Decimal(value)

    except (
        InvalidOperation,
        ValueError,
        TypeError
    ):
        return None

    if price <= 0:
        return None

    if price > MAX_PRICE:
        return None

    # Maximum 2 decimal places
    if price.as_tuple().exponent < -2:
        return None

    return price.quantize(
        Decimal("0.01")
    )


# =========================================================
# INTEGER ID VALIDATION
# =========================================================

def validate_id(value):
    """
    Safely convert an ID to integer.
    """

    try:
        value = int(value)

    except (
        ValueError,
        TypeError
    ):
        return None

    if value <= 0:
        return None

    return value


# =========================================================
# AUTHENTICATION
# =========================================================

def get_authenticated_shop(request):
    """
    Authentication + authorization helper.

    Checks:

    1. user_id exists in session
    2. user_id is valid
    3. account exists
    4. role is shop
    5. shop account is approved

    Returns:
        Register object if valid shop
        None otherwise
    """

    # -----------------------------------------------------
    # GET USER ID FROM SESSION
    # -----------------------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:
        return None

    # -----------------------------------------------------
    # VALIDATE USER ID
    # -----------------------------------------------------

    user_id = validate_id(
        user_id
    )

    if not user_id:
        request.session.flush()
        return None

    # -----------------------------------------------------
    # GET USER FROM DATABASE
    # -----------------------------------------------------

    try:

        user = Register.objects.get(
            id=user_id
        )

    except Register.DoesNotExist:

        request.session.flush()
        return None

    # -----------------------------------------------------
    # AUTHORIZATION - ROLE
    # -----------------------------------------------------

    if (
        not user.role
        or user.role.lower() != "shop"
    ):

        request.session.flush()
        return None

    # -----------------------------------------------------
    # AUTHORIZATION - APPROVAL
    # -----------------------------------------------------

    if user.approval_status != "approved":

        request.session.flush()
        return None

    return user


# =========================================================
# SHOP AUTHENTICATION + AUTHORIZATION DECORATOR
# =========================================================

def shop_required(view_func):
    """
    Protect Shop views.

    User must:

    - be logged in
    - have role = shop
    - have approval_status = approved

    Also disables browser caching.
    """

    @wraps(view_func)
    @never_cache
    def wrapper(
        request,
        *args,
        **kwargs
    ):

        # -------------------------------------------------
        # AUTHENTICATION
        # -------------------------------------------------

        user = get_authenticated_shop(
            request
        )

        if user is None:

            messages.warning(
                request,
                "Please login with an approved shop account."
            )

            return redirect(
                "login"
            )

        # -------------------------------------------------
        # REFRESH SESSION EXPIRY
        # -------------------------------------------------

        request.session.set_expiry(
            SESSION_TIMEOUT
        )

        # -------------------------------------------------
        # STORE CURRENT USER
        # -------------------------------------------------

        request.current_user = user

        # -------------------------------------------------
        # ALLOW VIEW
        # -------------------------------------------------

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# =========================================================
# SHOP DASHBOARD
# =========================================================

@shop_required
def home(request):

    user = request.current_user

    products = (
        Product.objects
        .filter(
            shop=user
        )
        .select_related(
            "category",
            "brand"
        )
        .order_by(
            "-created_at"
        )
    )

    total_products = products.count()

    total_orders = (
        OrderItem.objects
        .filter(
            product__shop=user
        )
        .values(
            "order_id"
        )
        .distinct()
        .count()
    )

    return render(
        request,
        "Shop/Shop_Dashboard.html",
        {
            "user": user,
            "products": products,
            "total_products": total_products,
            "total_orders": total_orders,
        }
    )


# =========================================================
# PRODUCTS
# =========================================================

@shop_required
def products(request):

    user = request.current_user

    product_list = (
        Product.objects
        .filter(
            shop=user
        )
        .select_related(
            "category",
            "brand"
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "Shop/products.html",
        {
            "user": user,
            "products": product_list,
            "total_products": product_list.count(),
        }
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@shop_required
def add_product(request):

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

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    if request.method != "POST":

        return render(
            request,
            "Shop/add_product.html",
            {
                "user": user,
                "categories": categories,
                "brands": brands,
            }
        )

    # -----------------------------------------------------
    # FORM DATA
    # -----------------------------------------------------

    name = request.POST.get(
        "name",
        ""
    ).strip()

    description = request.POST.get(
        "description",
        ""
    ).strip()

    price_value = request.POST.get(
        "price",
        ""
    ).strip()

    category_value = request.POST.get(
        "category",
        ""
    ).strip()

    brand_value = request.POST.get(
        "brand",
        ""
    ).strip()

    image = request.FILES.get(
        "image"
    )

    # -----------------------------------------------------
    # VALIDATE NAME
    # -----------------------------------------------------

    if not validate_name(
        name,
        MAX_PRODUCT_NAME_LENGTH
    ):

        return render(
            request,
            "Shop/add_product.html",
            {
                "user": user,
                "categories": categories,
                "brands": brands,
                "error": "Please enter a valid product name.",
            }
        )

    # -----------------------------------------------------
    # VALIDATE DESCRIPTION
    # -----------------------------------------------------

    if not validate_description(
        description,
        MAX_DESCRIPTION_LENGTH
    ):

        return render(
            request,
            "Shop/add_product.html",
            {
                "user": user,
                "categories": categories,
                "brands": brands,
                "error": "Please enter a valid product description.",
            }
        )

    # -----------------------------------------------------
    # VALIDATE PRICE
    # -----------------------------------------------------

    price = validate_price(
        price_value
    )

    if price is None:

        return render(
            request,
            "Shop/add_product.html",
            {
                "user": user,
                "categories": categories,
                "brands": brands,
                "error": "Please enter a valid price.",
            }
        )

    # -----------------------------------------------------
    # VALIDATE CATEGORY ID
    # -----------------------------------------------------

    category_id = validate_id(
        category_value
    )

    if not category_id:

        return render(
            request,
            "Shop/add_product.html",
            {
                "user": user,
                "categories": categories,
                "brands": brands,
                "error": "Please select a valid category.",
            }
        )

    # -----------------------------------------------------
    # VALIDATE BRAND ID
    # -----------------------------------------------------

    brand_id = validate_id(
        brand_value
    )

    if not brand_id:

        return render(
            request,
            "Shop/add_product.html",
            {
                "user": user,
                "categories": categories,
                "brands": brands,
                "error": "Please select a valid brand.",
            }
        )

    # -----------------------------------------------------
    # GET CATEGORY
    # -----------------------------------------------------

    category = get_object_or_404(
        Category,
        id=category_id
    )

    # -----------------------------------------------------
    # GET BRAND
    # -----------------------------------------------------

    brand = get_object_or_404(
        Brand,
        id=brand_id
    )

    # -----------------------------------------------------
    # CREATE PRODUCT
    # -----------------------------------------------------

    Product.objects.create(
        shop=user,
        name=name,
        description=description,
        price=price,
        image=image,
        category=category,
        brand=brand
    )

    messages.success(
        request,
        "Product added successfully."
    )

    return redirect(
        "shop_products"
    )


# =========================================================
# EDIT PRODUCT
# =========================================================

@shop_required
def edit_product(
    request,
    pk
):

    user = request.current_user

    product_id = validate_id(
        pk
    )

    if not product_id:

        messages.error(
            request,
            "Invalid product."
        )

        return redirect(
            "shop_products"
        )

    # -----------------------------------------------------
    # OBJECT-LEVEL AUTHORIZATION
    # -----------------------------------------------------

    product = get_object_or_404(
        Product,
        id=product_id,
        shop=user
    )

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

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    if request.method != "POST":

        return render(
            request,
            "Shop/edit_product.html",
            {
                "user": user,
                "product": product,
                "categories": categories,
                "brands": brands,
            }
        )

    # -----------------------------------------------------
    # FORM DATA
    # -----------------------------------------------------

    name = request.POST.get(
        "name",
        ""
    ).strip()

    description = request.POST.get(
        "description",
        ""
    ).strip()

    price_value = request.POST.get(
        "price",
        ""
    ).strip()

    category_value = request.POST.get(
        "category",
        ""
    ).strip()

    brand_value = request.POST.get(
        "brand",
        ""
    ).strip()

    image = request.FILES.get(
        "image"
    )

    # -----------------------------------------------------
    # NAME
    # -----------------------------------------------------

    if not validate_name(
        name,
        MAX_PRODUCT_NAME_LENGTH
    ):

        return render(
            request,
            "Shop/edit_product.html",
            {
                "user": user,
                "product": product,
                "categories": categories,
                "brands": brands,
                "error": "Please enter a valid product name.",
            }
        )

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    if not validate_description(
        description,
        MAX_DESCRIPTION_LENGTH
    ):

        return render(
            request,
            "Shop/edit_product.html",
            {
                "user": user,
                "product": product,
                "categories": categories,
                "brands": brands,
                "error": "Please enter a valid product description.",
            }
        )

    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    price = validate_price(
        price_value
    )

    if price is None:

        return render(
            request,
            "Shop/edit_product.html",
            {
                "user": user,
                "product": product,
                "categories": categories,
                "brands": brands,
                "error": "Please enter a valid price.",
            }
        )

    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    category_id = validate_id(
        category_value
    )

    if not category_id:

        return render(
            request,
            "Shop/edit_product.html",
            {
                "user": user,
                "product": product,
                "categories": categories,
                "brands": brands,
                "error": "Please select a valid category.",
            }
        )

    category = get_object_or_404(
        Category,
        id=category_id
    )

    # -----------------------------------------------------
    # BRAND
    # -----------------------------------------------------

    brand_id = validate_id(
        brand_value
    )

    if not brand_id:

        return render(
            request,
            "Shop/edit_product.html",
            {
                "user": user,
                "product": product,
                "categories": categories,
                "brands": brands,
                "error": "Please select a valid brand.",
            }
        )

    brand = get_object_or_404(
        Brand,
        id=brand_id
    )

    # -----------------------------------------------------
    # UPDATE
    # -----------------------------------------------------

    product.name = name
    product.description = description
    product.price = price
    product.category = category
    product.brand = brand

    if image:
        product.image = image

    product.save()

    messages.success(
        request,
        "Product updated successfully."
    )

    return redirect(
        "shop_products"
    )


# =========================================================
# DELETE PRODUCT
# =========================================================

@shop_required
@require_POST
def delete_product(
    request,
    pk
):

    user = request.current_user

    # -----------------------------------------------------
    # VALIDATE ID
    # -----------------------------------------------------

    product_id = validate_id(
        pk
    )

    if not product_id:

        messages.error(
            request,
            "Invalid product."
        )

        return redirect(
            "shop_products"
        )

    # -----------------------------------------------------
    # OBJECT-LEVEL AUTHORIZATION
    # -----------------------------------------------------

    product = get_object_or_404(
        Product,
        id=product_id,
        shop=user
    )

    product.delete()

    messages.success(
        request,
        "Product deleted successfully."
    )

    return redirect(
        "shop_products"
    )


# =========================================================
# CATEGORIES
# =========================================================

@shop_required
def categories(request):

    user = request.current_user

    category_list = (
        Category.objects
        .all()
        .order_by("name")
    )

    for category in category_list:

        category.product_count = (
            Product.objects
            .filter(
                category=category
            )
            .count()
        )

    return render(
        request,
        "Shop/categories.html",
        {
            "user": user,
            "categories": category_list,
        }
    )


# =========================================================
# ADD CATEGORY
# =========================================================

@shop_required
@require_POST
def add_category(request):

    name = request.POST.get(
        "name",
        ""
    ).strip()

    description = request.POST.get(
        "description",
        ""
    ).strip()

    image = request.FILES.get(
        "image"
    )

    # -----------------------------------------------------
    # NAME
    # -----------------------------------------------------

    if not validate_name(
        name,
        MAX_CATEGORY_NAME_LENGTH
    ):

        messages.error(
            request,
            "Please enter a valid category name."
        )

        return redirect(
            "shop_categories"
        )

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    if len(description) > MAX_CATEGORY_DESCRIPTION_LENGTH:

        messages.error(
            request,
            "Category description is too long."
        )

        return redirect(
            "shop_categories"
        )

    # -----------------------------------------------------
    # DUPLICATE
    # -----------------------------------------------------

    if Category.objects.filter(
        name__iexact=name
    ).exists():

        messages.error(
            request,
            "This category already exists."
        )

        return redirect(
            "shop_categories"
        )

    # -----------------------------------------------------
    # CREATE
    # -----------------------------------------------------

    Category.objects.create(
        name=name,
        description=description,
        image=image
    )

    messages.success(
        request,
        "Category added successfully."
    )

    return redirect(
        "shop_categories"
    )


# =========================================================
# CATEGORY PRODUCTS
# =========================================================

@shop_required
def category_products(
    request,
    pk
):

    user = request.current_user

    category_id = validate_id(
        pk
    )

    if not category_id:

        messages.error(
            request,
            "Invalid category."
        )

        return redirect(
            "shop_categories"
        )

    category = get_object_or_404(
        Category,
        id=category_id
    )

    product_list = (
        Product.objects
        .filter(
            category=category
        )
        .select_related(
            "brand",
            "shop"
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "Shop/category_products.html",
        {
            "user": user,
            "category": category,
            "products": product_list,
        }
    )


# =========================================================
# BRANDS
# =========================================================

@shop_required
def brands(request):

    user = request.current_user

    brand_list = (
        Brand.objects
        .all()
        .order_by("name")
    )

    for brand in brand_list:

        brand.product_count = (
            Product.objects
            .filter(
                brand=brand
            )
            .count()
        )

    return render(
        request,
        "Shop/brands.html",
        {
            "user": user,
            "brands": brand_list,
        }
    )


# =========================================================
# ADD BRAND
# =========================================================

@shop_required
@require_POST
def add_brand(request):

    name = request.POST.get(
        "name",
        ""
    ).strip()

    description = request.POST.get(
        "description",
        ""
    ).strip()

    logo = request.FILES.get(
        "logo"
    )

    # -----------------------------------------------------
    # NAME
    # -----------------------------------------------------

    if not validate_name(
        name,
        MAX_BRAND_NAME_LENGTH
    ):

        messages.error(
            request,
            "Please enter a valid brand name."
        )

        return redirect(
            "shop_brands"
        )

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    if len(description) > MAX_BRAND_DESCRIPTION_LENGTH:

        messages.error(
            request,
            "Brand description is too long."
        )

        return redirect(
            "shop_brands"
        )

    # -----------------------------------------------------
    # DUPLICATE
    # -----------------------------------------------------

    if Brand.objects.filter(
        name__iexact=name
    ).exists():

        messages.error(
            request,
            "This brand already exists."
        )

        return redirect(
            "shop_brands"
        )

    # -----------------------------------------------------
    # CREATE
    # -----------------------------------------------------

    Brand.objects.create(
        name=name,
        description=description,
        logo=logo
    )

    messages.success(
        request,
        "Brand added successfully."
    )

    return redirect(
        "shop_brands"
    )


# =========================================================
# BRAND PRODUCTS
# =========================================================

@shop_required
def brand_products(
    request,
    pk
):

    user = request.current_user

    brand_id = validate_id(
        pk
    )

    if not brand_id:

        messages.error(
            request,
            "Invalid brand."
        )

        return redirect(
            "shop_brands"
        )

    brand = get_object_or_404(
        Brand,
        id=brand_id
    )

    product_list = (
        Product.objects
        .filter(
            brand=brand
        )
        .select_related(
            "category",
            "shop"
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "Shop/brand_products.html",
        {
            "user": user,
            "brand": brand,
            "products": product_list,
        }
    )


# =========================================================
# SHOP REVIEWS
# =========================================================

@shop_required
def reviews(request):

    user = request.current_user

    review_list = (
        Review.objects
        .filter(
            product__shop=user
        )
        .select_related(
            "product",
            "product__category",
            "product__brand",
            "user"
        )
        .order_by(
            "-created_at"
        )
    )

    total_reviews = review_list.count()

    average_rating = Decimal("0.0")

    if total_reviews:

        total_rating = sum(
            review.rating
            for review in review_list
        )

        average_rating = (
            Decimal(str(total_rating))
            /
            Decimal(str(total_reviews))
        ).quantize(
            Decimal("0.1")
        )

    return render(
        request,
        "Shop/reviews.html",
        {
            "user": user,
            "reviews": review_list,
            "total_reviews": total_reviews,
            "average_rating": average_rating,
        }
    )


# =========================================================
# REPLY TO REVIEW
# =========================================================

@shop_required
@require_POST
def reply_review(
    request,
    review_id
):

    user = request.current_user

    # -----------------------------------------------------
    # VALIDATE REVIEW ID
    # -----------------------------------------------------

    review_pk = validate_id(
        review_id
    )

    if not review_pk:

        messages.error(
            request,
            "Invalid review."
        )

        return redirect(
            "shop_reviews"
        )

    # -----------------------------------------------------
    # GET REVIEW
    # -----------------------------------------------------

    review = (
        Review.objects
        .select_related(
            "product",
            "user"
        )
        .filter(
            id=review_pk,
            product__shop=user
        )
        .first()
    )

    # -----------------------------------------------------
    # OBJECT-LEVEL AUTHORIZATION
    # -----------------------------------------------------

    if not review:

        messages.error(
            request,
            "You are not authorized to reply to this review."
        )

        return redirect(
            "shop_reviews"
        )

    # -----------------------------------------------------
    # GET REPLY
    # -----------------------------------------------------

    reply = request.POST.get(
        "shop_reply",
        ""
    ).strip()

    # -----------------------------------------------------
    # VALIDATE REPLY
    # -----------------------------------------------------

    if not reply:

        messages.error(
            request,
            "Reply cannot be empty."
        )

        return redirect(
            "shop_reviews"
        )

    if len(reply) > MAX_REVIEW_REPLY_LENGTH:

        messages.error(
            request,
            "Reply cannot exceed 1000 characters."
        )

        return redirect(
            "shop_reviews"
        )

    # -----------------------------------------------------
    # SAVE REPLY
    # -----------------------------------------------------

    review.shop_reply = reply

    review.save(
        update_fields=[
            "shop_reply"
        ]
    )

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    messages.success(
        request,
        "Your reply has been posted successfully."
    )

    return redirect(
        "shop_reviews"
    )


# =========================================================
# SHOP ORDERS
# =========================================================

@shop_required
def orders(request):

    user = request.current_user

    order_list = list(
        Order.objects
        .filter(
            items__product__shop=user
        )
        .select_related(
            "user"
        )
        .prefetch_related(
            "items",
            "items__product"
        )
        .distinct()
        .order_by(
            "-created_at"
        )
    )

    # -----------------------------------------------------
    # SHOP PRODUCTS ONLY
    # -----------------------------------------------------

    for order in order_list:

        order.shop_items = [
            item
            for item in order.items.all()
            if (
                item.product
                and item.product.shop_id == user.id
            )
        ]

    # -----------------------------------------------------
    # COUNTS
    # -----------------------------------------------------

    total_orders = len(
        order_list
    )

    pending_orders = sum(
        1
        for order in order_list
        if order.status == "Pending"
    )

    processing_orders = sum(
        1
        for order in order_list
        if order.status == "Processing"
    )

    accepted_orders = sum(
        1
        for order in order_list
        if order.status == "Accepted"
    )

    rejected_orders = sum(
        1
        for order in order_list
        if order.status == "Rejected"
    )

    shipped_orders = sum(
        1
        for order in order_list
        if order.status == "Shipped"
    )

    delivered_orders = sum(
        1
        for order in order_list
        if order.status == "Delivered"
    )

    cancelled_orders = sum(
        1
        for order in order_list
        if order.status == "Cancelled"
    )

    return render(
        request,
        "Shop/orders.html",
        {
            "user": user,
            "orders": order_list,

            "total_orders": total_orders,

            "pending_orders": pending_orders,

            "processing_orders": processing_orders,

            "accepted_orders": accepted_orders,

            "rejected_orders": rejected_orders,

            "shipped_orders": shipped_orders,

            "delivered_orders": delivered_orders,

            "cancelled_orders": cancelled_orders,
        }
    )


# =========================================================
# UPDATE ORDER STATUS
# =========================================================

@shop_required
@require_POST
def update_order_status(
    request,
    order_id
):

    user = request.current_user

    # -----------------------------------------------------
    # VALIDATE ORDER ID
    # -----------------------------------------------------

    order_id = validate_id(
        order_id
    )

    if not order_id:

        messages.error(
            request,
            "Invalid order."
        )

        return redirect(
            "shop_orders"
        )

    # -----------------------------------------------------
    # OBJECT-LEVEL AUTHORIZATION
    # -----------------------------------------------------

    order = (
        Order.objects
        .filter(
            id=order_id,
            items__product__shop=user
        )
        .distinct()
        .first()
    )

    if not order:

        messages.error(
            request,
            "You are not authorized to update this order."
        )

        return redirect(
            "shop_orders"
        )

    # -----------------------------------------------------
    # NEW STATUS
    # -----------------------------------------------------

    new_status = request.POST.get(
        "status",
        ""
    ).strip()

    # -----------------------------------------------------
    # VALID STATUSES
    # -----------------------------------------------------

    allowed_statuses = [
        "Pending",
        "Processing",
        "Accepted",
        "Rejected",
        "Shipped",
        "Delivered",
        "Cancelled",
    ]

    if new_status not in allowed_statuses:

        messages.error(
            request,
            "Invalid order status."
        )

        return redirect(
            "shop_orders"
        )

    current_status = order.status

    # -----------------------------------------------------
    # SAME STATUS
    # -----------------------------------------------------

    if current_status == new_status:

        messages.warning(
            request,
            f"Order #{order.id} is already {new_status}."
        )

        return redirect(
            "shop_orders"
        )

    # =====================================================
    # STATUS TRANSITIONS
    # =====================================================

    allowed_transitions = {

        "Pending": [
            "Processing",
            "Rejected",
            "Cancelled",
        ],

        "Processing": [
            "Shipped",
            "Cancelled",
        ],

        "Accepted": [
            "Shipped",
            "Cancelled",
        ],

        "Shipped": [
            "Delivered",
        ],

        "Delivered": [],

        "Rejected": [],

        "Cancelled": [],
    }

    # -----------------------------------------------------
    # CHECK TRANSITION
    # -----------------------------------------------------

    if new_status not in allowed_transitions.get(
        current_status,
        []
    ):

        messages.error(
            request,
            (
                f"Order #{order.id} cannot be changed "
                f"from {current_status} to {new_status}."
            )
        )

        return redirect(
            "shop_orders"
        )

    # =====================================================
    # UPDATE STATUS
    # =====================================================

    order.status = new_status

    order.save(
        update_fields=[
            "status"
        ]
    )

    # =====================================================
    # SUCCESS MESSAGE
    # =====================================================

    success_messages = {

        "Processing":
            f"Order #{order.id} is now being processed successfully.",

        "Shipped":
            f"Order #{order.id} has been marked as shipped successfully.",

        "Delivered":
            f"Order #{order.id} has been marked as delivered successfully.",

        "Cancelled":
            f"Order #{order.id} has been cancelled successfully.",

        "Rejected":
            f"Order #{order.id} has been rejected successfully.",

        "Accepted":
            f"Order #{order.id} has been accepted successfully.",
    }

    messages.success(
        request,
        success_messages.get(
            new_status,
            f"Order #{order.id} status updated successfully."
        )
    )

    return redirect(
        "shop_orders"
    )


# =========================================================
# SHOP LOGOUT
# =========================================================

@require_POST
@never_cache
def logout(request):
    """
    Secure Shop logout.

    1. Completely destroys the session.
    2. Prevents cached logout response.
    3. Redirects to login.

    IMPORTANT:
    Do not add a Django messages.success() after
    session.flush(), because Django messages normally
    use session storage and this can create a new session.
    """

    # -----------------------------------------------------
    # COMPLETELY CLEAR SESSION
    # -----------------------------------------------------

    request.session.flush()

    # -----------------------------------------------------
    # REDIRECT
    # -----------------------------------------------------

    return redirect(
        "login"
    )