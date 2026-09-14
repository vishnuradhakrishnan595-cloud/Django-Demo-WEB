from decimal import Decimal
from functools import wraps
import re

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.db import transaction

from django.contrib import messages

from django.contrib.auth.hashers import (
    check_password,
    make_password
)

from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from django.views.decorators.http import (
    require_POST
)

from django.views.decorators.cache import never_cache

from PIL import Image

from Guest.models import Register

from Shop.models import (
    Product,
    Category,
    Brand,
    Review
)

from .models import (
    Profile,
    Order,
    Cart,
    CartItem,
    OrderItem
)


# =========================================================
# CONSTANTS
# =========================================================

SESSION_TIMEOUT = 7200

MAX_CART_QUANTITY = 99

MAX_IMAGE_SIZE = 2 * 1024 * 1024

MAX_NAME_LENGTH = 100
MAX_CITY_LENGTH = 100
MAX_ADDRESS_LENGTH = 500

MAX_COMMENT_LENGTH = 500

MAX_PASSWORD_LENGTH = 128

MAX_PRODUCT_ID = 2147483647


# =========================================================
# VALIDATION HELPERS
# =========================================================

def validate_name(name):

    if not name:
        return False

    if len(name) < 2:
        return False

    if len(name) > MAX_NAME_LENGTH:
        return False

    pattern = r"^[A-Za-zÀ-ÿ .'-]+$"

    return bool(
        re.fullmatch(
            pattern,
            name
        )
    )


def validate_city(city):

    if not city:
        return False

    if len(city) < 2:
        return False

    if len(city) > MAX_CITY_LENGTH:
        return False

    pattern = r"^[A-Za-zÀ-ÿ .'-]+$"

    return bool(
        re.fullmatch(
            pattern,
            city
        )
    )


def validate_phone(phone):

    if not phone:
        return False

    pattern = r"^[6-9][0-9]{9}$"

    return bool(
        re.fullmatch(
            pattern,
            phone
        )
    )


def validate_pincode(pincode):

    if not pincode:
        return False

    pattern = r"^[1-9][0-9]{5}$"

    return bool(
        re.fullmatch(
            pattern,
            pincode
        )
    )


def validate_address(address):

    if not address:
        return False

    if len(address) < 5:
        return False

    if len(address) > MAX_ADDRESS_LENGTH:
        return False

    return True


def validate_password(password):

    if not password:
        return False

    if len(password) < 8:
        return False

    if len(password) > MAX_PASSWORD_LENGTH:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    return True


def validate_positive_id(value):

    try:
        value = int(value)

    except (
        ValueError,
        TypeError
    ):
        return None

    if value <= 0:
        return None

    if value > MAX_PRODUCT_ID:
        return None

    return value


def validate_image(image):

    if not image:
        return True, ""

    # -----------------------------------------------------
    # File size
    # -----------------------------------------------------

    if image.size > MAX_IMAGE_SIZE:

        return (
            False,
            "Image must be less than 2 MB."
        )

    # -----------------------------------------------------
    # Content type
    # -----------------------------------------------------

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp"
    }

    if image.content_type not in allowed_types:

        return (
            False,
            "Only JPG, PNG and WEBP images are allowed."
        )

    # -----------------------------------------------------
    # Validate actual image
    # -----------------------------------------------------

    try:

        image.seek(0)

        img = Image.open(image)

        img.verify()

        image.seek(0)

    except Exception:

        return (
            False,
            "Invalid image file."
        )

    return True, ""


# =========================================================
# GET GOOGLE EMAIL
# =========================================================

def get_google_email(request):

    """
    Get Google email from Django/allauth.

    Priority:

    1. request.user.email
    2. SocialAccount.extra_data["email"]
    """

    # -----------------------------------------------------
    # Method 1
    # -----------------------------------------------------

    try:

        email = (
            request.user.email or ""
        ).strip().lower()

    except AttributeError:

        email = ""

    if email:

        return email

    # -----------------------------------------------------
    # Method 2
    # -----------------------------------------------------

    try:

        from allauth.socialaccount.models import (
            SocialAccount
        )

        social_account = (
            SocialAccount.objects
            .filter(
                user=request.user,
                provider="google"
            )
            .first()
        )

        if social_account:

            extra_data = (
                social_account.extra_data or {}
            )

            email = (
                extra_data.get("email") or ""
            ).strip().lower()

            if email:

                return email

    except Exception:

        pass

    return ""


# =========================================================
# GET CURRENT MINISHOP USER
# =========================================================

def get_authenticated_user(request):

    """
    Authenticate the custom MiniShop user
    from the session.

    Checks:

    - user_id exists
    - user_id is valid
    - Register account exists
    - role is user
    - account is approved
    """

    user_id = request.session.get(
        "user_id"
    )

    # -----------------------------------------------------
    # No session
    # -----------------------------------------------------

    if not user_id:

        return None

    # -----------------------------------------------------
    # Validate ID
    # -----------------------------------------------------

    user_id = validate_positive_id(
        user_id
    )

    if not user_id:

        request.session.flush()

        return None

    # -----------------------------------------------------
    # Get database user
    # -----------------------------------------------------

    try:

        user = Register.objects.get(
            id=user_id
        )

    except Register.DoesNotExist:

        request.session.flush()

        return None

    # -----------------------------------------------------
    # Role authorization
    # -----------------------------------------------------

    if (
        not user.role
        or user.role.lower() != "user"
    ):

        request.session.flush()

        return None

    # -----------------------------------------------------
    # Approval authorization
    # -----------------------------------------------------

    if user.approval_status != "approved":

        request.session.flush()

        return None

    # -----------------------------------------------------
    # Refresh session timeout
    # -----------------------------------------------------

    request.session.set_expiry(
        SESSION_TIMEOUT
    )

    return user


# =========================================================
# ADD SECURITY HEADERS
# =========================================================

def secure_no_cache(response):

    """
    Prevent authenticated pages from being stored
    in the browser cache.

    This helps prevent the browser Back button
    from showing an old authenticated page after logout.
    """

    response["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, "
        "max-age=0, private"
    )

    response["Pragma"] = "no-cache"

    response["Expires"] = "0"

    return response


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(view_func):

    @wraps(view_func)
    def wrapper(
        request,
        *args,
        **kwargs
    ):

        # =================================================
        # 1. EXISTING MINISHOP SESSION
        # =================================================

        custom_user = get_authenticated_user(
            request
        )

        if custom_user:

            request.current_user = custom_user

            response = view_func(
                request,
                *args,
                **kwargs
            )

            return secure_no_cache(
                response
            )

        # =================================================
        # 2. GOOGLE / DJANGO ALLAUTH SESSION
        # =================================================

        if (
            hasattr(request, "user")
            and request.user.is_authenticated
        ):

            google_email = get_google_email(
                request
            )

            # -------------------------------------------------
            # Google email unavailable
            # -------------------------------------------------

            if not google_email:

                messages.error(
                    request,
                    (
                        "Google login succeeded, but the "
                        "Google email address could not be obtained. "
                        "Please try Google login again."
                    )
                )

                response = redirect(
                    "login"
                )

                return secure_no_cache(
                    response
                )

            # -------------------------------------------------
            # Find MiniShop account
            # -------------------------------------------------

            try:

                custom_user = (
                    Register.objects
                    .get(
                        email__iexact=google_email
                    )
                )

            except Register.DoesNotExist:

                messages.warning(
                    request,
                    (
                        "Your Google account is authenticated, "
                        "but no MiniShop account exists for "
                        f"{google_email}. Please register first."
                    )
                )

                response = redirect(
                    "login"
                )

                return secure_no_cache(
                    response
                )

            # -------------------------------------------------
            # Role check
            # -------------------------------------------------

            if (
                not custom_user.role
                or custom_user.role.lower() != "user"
            ):

                messages.error(
                    request,
                    (
                        "This Google account is not registered "
                        "as a MiniShop user."
                    )
                )

                response = redirect(
                    "login"
                )

                return secure_no_cache(
                    response
                )

            # -------------------------------------------------
            # Approval check
            # -------------------------------------------------

            if custom_user.approval_status != "approved":

                messages.warning(
                    request,
                    (
                        "Your MiniShop account is not approved yet. "
                        "Please wait for admin approval."
                    )
                )

                response = redirect(
                    "login"
                )

                return secure_no_cache(
                    response
                )

            # =================================================
            # SESSION FIXATION PROTECTION
            # =================================================

            request.session.cycle_key()

            # =================================================
            # CREATE MINISHOP SESSION
            # =================================================

            request.session["user_id"] = (
                custom_user.id
            )

            request.session["user_name"] = (
                custom_user.name
            )

            request.session["user_email"] = (
                custom_user.email
            )

            request.session["user_role"] = (
                custom_user.role
            )

            # Compatibility
            request.session["role"] = (
                custom_user.role
            )

            request.session.set_expiry(
                SESSION_TIMEOUT
            )

            request.current_user = custom_user

            response = view_func(
                request,
                *args,
                **kwargs
            )

            return secure_no_cache(
                response
            )

        # =================================================
        # 3. NOT AUTHENTICATED
        # =================================================

        messages.warning(
            request,
            "Please login to continue."
        )

        response = redirect(
            "login"
        )

        return secure_no_cache(
            response
        )

    return wrapper


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
            "brand"
        )
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
            "products": products
        }
    )


# =========================================================
# PRODUCTS
# =========================================================

@login_required
def products(request):

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

    product_list = (
        Product.objects
        .select_related(
            "shop",
            "category",
            "brand"
        )
        .order_by("-created_at")
    )

    category_id = (
        request.GET.get(
            "category",
            ""
        ).strip()
    )

    brand_id = (
        request.GET.get(
            "brand",
            ""
        ).strip()
    )

    selected_category = None
    selected_brand = None

    # =====================================================
    # CATEGORY FILTER
    # =====================================================

    if category_id:

        category_pk = validate_positive_id(
            category_id
        )

        if category_pk:

            selected_category = (
                Category.objects
                .filter(
                    id=category_pk
                )
                .first()
            )

            if selected_category:

                product_list = (
                    product_list
                    .filter(
                        category_id=selected_category.id
                    )
                )

    # =====================================================
    # BRAND FILTER
    # =====================================================

    if brand_id:

        brand_pk = validate_positive_id(
            brand_id
        )

        if brand_pk:

            selected_brand = (
                Brand.objects
                .filter(
                    id=brand_pk
                )
                .first()
            )

            if selected_brand:

                product_list = (
                    product_list
                    .filter(
                        brand_id=selected_brand.id
                    )
                )

    # =====================================================
    # PAGE TITLE
    # =====================================================

    if (
        selected_category
        and selected_brand
    ):

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

    # =====================================================
    # PAGE DESCRIPTION
    # =====================================================

    if (
        selected_category
        and selected_brand
    ):

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

    return render(
        request,
        "User/products.html",
        {
            "user": user,
            "products": product_list,
            "categories": categories,
            "brands": brands,
            "selected_category": selected_category,
            "selected_brand": selected_brand,
            "page_title": page_title,
            "page_description": page_description,
            "category_id": category_id,
            "brand_id": brand_id
        }
    )


# =========================================================
# PRODUCT DETAIL
# =========================================================

@login_required
def product_detail(request, pk):

    user = request.current_user

    product_id = validate_positive_id(
        pk
    )

    if not product_id:

        messages.error(
            request,
            "Invalid product."
        )

        return redirect(
            "user_products"
        )

    product = get_object_or_404(
        Product.objects.select_related(
            "shop",
            "category",
            "brand"
        ),
        id=product_id
    )

    reviews = (
        product.reviews
        .select_related("user")
        .order_by("-id")
    )

    review_count = reviews.count()

    average_rating = Decimal("0.0")

    if review_count:

        total_rating = sum(
            review.rating
            for review in reviews
        )

        average_rating = (
            Decimal(str(total_rating))
            /
            Decimal(str(review_count))
        )

        average_rating = average_rating.quantize(
            Decimal("0.1")
        )

    return render(
        request,
        "User/product_detail.html",
        {
            "user": user,
            "product": product,
            "reviews": reviews,
            "average_rating": average_rating,
            "review_count": review_count
        }
    )


# =========================================================
# SUBMIT REVIEW
# =========================================================

@login_required
@require_POST
def submit_review(request, pk):

    user = request.current_user

    product_id = validate_positive_id(
        pk
    )

    if not product_id:

        return redirect(
            "user_products"
        )

    product = get_object_or_404(
        Product,
        id=product_id
    )

    rating = (
        request.POST.get(
            "rating",
            ""
        ).strip()
    )

    comment = (
        request.POST.get(
            "comment",
            ""
        ).strip()
    )

    # =====================================================
    # RATING
    # =====================================================

    try:

        rating_value = int(
            rating
        )

    except (
        ValueError,
        TypeError
    ):

        messages.error(
            request,
            "Invalid rating."
        )

        return redirect(
            "product_detail",
            pk=product.id
        )

    if (
        rating_value < 1
        or rating_value > 5
    ):

        messages.error(
            request,
            "Rating must be between 1 and 5."
        )

        return redirect(
            "product_detail",
            pk=product.id
        )

    # =====================================================
    # COMMENT
    # =====================================================

    if len(comment) > MAX_COMMENT_LENGTH:

        messages.error(
            request,
            "Review comment is too long."
        )

        return redirect(
            "product_detail",
            pk=product.id
        )

    # =====================================================
    # CREATE / UPDATE REVIEW
    # =====================================================

    review, created = (
        Review.objects
        .update_or_create(
            product=product,
            user=user,
            defaults={
                "rating": rating_value,
                "comment": comment
            }
        )
    )

    if created:

        messages.success(
            request,
            "Review added successfully."
        )

    else:

        messages.success(
            request,
            "Review updated successfully."
        )

    return redirect(
        "product_detail",
        pk=product.id
    )


# =========================================================
# PROFILE
# =========================================================

@login_required
def profile(request):

    user = request.current_user

    profile, created = (
        Profile.objects
        .get_or_create(
            user=user
        )
    )

    order_count = (
        Order.objects
        .filter(
            user=user
        )
        .count()
    )

    cart_count = sum(
        CartItem.objects
        .filter(
            cart__user=user
        )
        .values_list(
            "quantity",
            flat=True
        )
    )

    return render(
        request,
        "User/profile.html",
        {
            "user": user,
            "profile": profile,
            "order_count": order_count,
            "cart_count": cart_count
        }
    )


# =========================================================
# EDIT PROFILE
# =========================================================

@login_required
def edit_profile(request):

    user = request.current_user

    profile, created = (
        Profile.objects
        .get_or_create(
            user=user
        )
    )

    if request.method == "POST":

        name = (
            request.POST.get(
                "name",
                ""
            ).strip()
        )

        email = (
            request.POST.get(
                "email",
                ""
            ).strip().lower()
        )

        phone = (
            request.POST.get(
                "phone",
                ""
            ).strip()
        )

        address = (
            request.POST.get(
                "address",
                ""
            ).strip()
        )

        image = request.FILES.get(
            "image"
        )

        # =================================================
        # NAME
        # =================================================

        if not validate_name(name):

            return render(
                request,
                "User/edit_profile.html",
                {
                    "user": user,
                    "profile": profile,
                    "error": (
                        "Please enter a valid name."
                    )
                }
            )

        # =================================================
        # EMAIL
        # =================================================

        try:

            validate_email(email)

        except ValidationError:

            return render(
                request,
                "User/edit_profile.html",
                {
                    "user": user,
                    "profile": profile,
                    "error": (
                        "Please enter a valid email address."
                    )
                }
            )

        # =================================================
        # PHONE
        # =================================================

        if phone and not validate_phone(phone):

            return render(
                request,
                "User/edit_profile.html",
                {
                    "user": user,
                    "profile": profile,
                    "error": (
                        "Enter a valid 10-digit phone number."
                    )
                }
            )

        # =================================================
        # ADDRESS
        # =================================================

        if address and not validate_address(address):

            return render(
                request,
                "User/edit_profile.html",
                {
                    "user": user,
                    "profile": profile,
                    "error": (
                        "Please enter a valid address."
                    )
                }
            )

        # =================================================
        # EMAIL DUPLICATE CHECK
        # =================================================

        existing_user = (
            Register.objects
            .filter(
                email__iexact=email
            )
            .exclude(
                id=user.id
            )
            .exists()
        )

        if existing_user:

            return render(
                request,
                "User/edit_profile.html",
                {
                    "user": user,
                    "profile": profile,
                    "error": (
                        "This email is already registered."
                    )
                }
            )

        # =================================================
        # IMAGE VALIDATION
        # =================================================

        if image:

            valid, error_message = validate_image(
                image
            )

            if not valid:

                return render(
                    request,
                    "User/edit_profile.html",
                    {
                        "user": user,
                        "profile": profile,
                        "error": error_message
                    }
                )

        # =================================================
        # SAVE USER
        # =================================================

        user.name = name

        user.email = email

        user.save(
            update_fields=[
                "name",
                "email"
            ]
        )

        # =================================================
        # SAVE PROFILE
        # =================================================

        profile.phone = phone

        profile.address = address

        if image:

            profile.image = image

        profile.save()

        # =================================================
        # REFRESH SESSION
        # =================================================

        request.session.cycle_key()

        request.session["user_id"] = user.id

        request.session["user_name"] = user.name

        request.session["user_email"] = user.email

        request.session["user_role"] = user.role

        request.session["role"] = user.role

        request.session.set_expiry(
            SESSION_TIMEOUT
        )

        messages.success(
            request,
            "Profile updated successfully."
        )

        return redirect(
            "profile"
        )

    return render(
        request,
        "User/edit_profile.html",
        {
            "user": user,
            "profile": profile
        }
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@login_required
def change_password(request):

    user = request.current_user

    if request.method == "POST":

        current_password = request.POST.get(
            "current_password",
            ""
        )

        new_password = request.POST.get(
            "new_password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        # =================================================
        # CURRENT PASSWORD
        # =================================================

        if not current_password:

            return render(
                request,
                "User/change_password.html",
                {
                    "user": user,
                    "error": (
                        "Current password is required."
                    )
                }
            )

        if not check_password(
            current_password,
            user.password
        ):

            return render(
                request,
                "User/change_password.html",
                {
                    "user": user,
                    "error": (
                        "Current password is incorrect."
                    )
                }
            )

        # =================================================
        # NEW PASSWORD
        # =================================================

        if not validate_password(
            new_password
        ):

            return render(
                request,
                "User/change_password.html",
                {
                    "user": user,
                    "error": (
                        "Password must contain at least "
                        "8 characters, one uppercase letter, "
                        "one lowercase letter and one number."
                    )
                }
            )

        # =================================================
        # CONFIRM PASSWORD
        # =================================================

        if new_password != confirm_password:

            return render(
                request,
                "User/change_password.html",
                {
                    "user": user,
                    "error": (
                        "New passwords do not match."
                    )
                }
            )

        # =================================================
        # SAME PASSWORD
        # =================================================

        if check_password(
            new_password,
            user.password
        ):

            return render(
                request,
                "User/change_password.html",
                {
                    "user": user,
                    "error": (
                        "New password must be different "
                        "from your current password."
                    )
                }
            )

        # =================================================
        # HASH PASSWORD
        # =================================================

        user.password = make_password(
            new_password
        )

        user.save(
            update_fields=[
                "password"
            ]
        )

        # =================================================
        # SESSION ROTATION
        # =================================================

        request.session.cycle_key()

        request.session["user_id"] = user.id

        request.session["user_name"] = user.name

        request.session["user_email"] = user.email

        request.session["user_role"] = user.role

        request.session["role"] = user.role

        request.session.set_expiry(
            SESSION_TIMEOUT
        )

        messages.success(
            request,
            "Password changed successfully."
        )

        return redirect(
            "profile"
        )

    return render(
        request,
        "User/change_password.html",
        {
            "user": user
        }
    )


# =========================================================
# CART
# =========================================================

@login_required
def cart(request):

    user = request.current_user

    cart_obj, created = (
        Cart.objects
        .get_or_create(
            user=user
        )
    )

    items = (
        cart_obj.items
        .select_related("product")
        .all()
    )

    total = Decimal("0.00")

    for item in items:

        total += (
            item.product.price
            *
            item.quantity
        )

    return render(
        request,
        "User/cart.html",
        {
            "user": user,
            "cart": cart_obj,
            "items": items,
            "total": total
        }
    )


# =========================================================
# ADD TO CART
# =========================================================

@login_required
@require_POST
def add_to_cart(request, pk):

    user = request.current_user

    product_id = validate_positive_id(
        pk
    )

    if not product_id:

        messages.error(
            request,
            "Invalid product."
        )

        return redirect(
            "user_products"
        )

    product = get_object_or_404(
        Product,
        id=product_id
    )

    quantity_value = (
        request.POST.get(
            "quantity",
            "1"
        ).strip()
    )

    try:

        quantity = int(
            quantity_value
        )

    except (
        ValueError,
        TypeError
    ):

        messages.error(
            request,
            "Invalid quantity."
        )

        return redirect(
            "user_products"
        )

    if (
        quantity < 1
        or quantity > MAX_CART_QUANTITY
    ):

        messages.error(
            request,
            f"Quantity must be between 1 and {MAX_CART_QUANTITY}."
        )

        return redirect(
            "user_products"
        )

    # =====================================================
    # GET USER CART
    # =====================================================

    cart_obj, created = (
        Cart.objects
        .get_or_create(
            user=user
        )
    )

    # =====================================================
    # CREATE / UPDATE CART ITEM
    # =====================================================

    cart_item, created = (
        CartItem.objects
        .get_or_create(
            cart=cart_obj,
            product=product,
            defaults={
                "quantity": quantity
            }
        )
    )

    if not created:

        new_quantity = (
            cart_item.quantity
            +
            quantity
        )

        if new_quantity > MAX_CART_QUANTITY:

            messages.error(
                request,
                f"Maximum quantity is {MAX_CART_QUANTITY}."
            )

            return redirect(
                "cart"
            )

        cart_item.quantity = new_quantity

        cart_item.save(
            update_fields=[
                "quantity"
            ]
        )

    messages.success(
        request,
        "Product added to cart."
    )

    return redirect(
        "cart"
    )


# =========================================================
# UPDATE CART
# =========================================================

@login_required
@require_POST
def update_cart(request, item_id):

    user = request.current_user

    item_pk = validate_positive_id(
        item_id
    )

    if not item_pk:

        return redirect(
            "cart"
        )

    # =====================================================
    # OBJECT LEVEL AUTHORIZATION
    # =====================================================

    cart_item = get_object_or_404(
        CartItem,
        id=item_pk,
        cart__user=user
    )

    quantity_value = (
        request.POST.get(
            "quantity",
            "1"
        ).strip()
    )

    try:

        quantity = int(
            quantity_value
        )

    except (
        ValueError,
        TypeError
    ):

        messages.error(
            request,
            "Invalid quantity."
        )

        return redirect(
            "cart"
        )

    # =====================================================
    # DELETE WHEN ZERO
    # =====================================================

    if quantity <= 0:

        cart_item.delete()

        messages.success(
            request,
            "Product removed from cart."
        )

        return redirect(
            "cart"
        )

    # =====================================================
    # MAX QUANTITY
    # =====================================================

    if quantity > MAX_CART_QUANTITY:

        messages.error(
            request,
            f"Maximum quantity is {MAX_CART_QUANTITY}."
        )

        return redirect(
            "cart"
        )

    cart_item.quantity = quantity

    cart_item.save(
        update_fields=[
            "quantity"
        ]
    )

    messages.success(
        request,
        "Cart updated successfully."
    )

    return redirect(
        "cart"
    )


# =========================================================
# REMOVE FROM CART
# =========================================================

@login_required
@require_POST
def remove_from_cart(request, item_id):

    user = request.current_user

    item_pk = validate_positive_id(
        item_id
    )

    if not item_pk:

        return redirect(
            "cart"
        )

    # =====================================================
    # OBJECT LEVEL AUTHORIZATION
    # =====================================================

    cart_item = get_object_or_404(
        CartItem,
        id=item_pk,
        cart__user=user
    )

    cart_item.delete()

    messages.success(
        request,
        "Product removed from cart."
    )

    return redirect(
        "cart"
    )


# =========================================================
# CHECKOUT
# =========================================================

@login_required
def checkout(request):

    user = request.current_user

    cart_obj, created = (
        Cart.objects
        .get_or_create(
            user=user
        )
    )

    items = (
        cart_obj.items
        .select_related("product")
        .all()
    )

    if not items.exists():

        messages.warning(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )

    total = Decimal("0.00")

    for item in items:

        if (
            item.quantity < 1
            or item.quantity > MAX_CART_QUANTITY
        ):

            messages.error(
                request,
                "Invalid cart quantity."
            )

            return redirect(
                "cart"
            )

        total += (
            item.product.price
            *
            item.quantity
        )

    profile, created = (
        Profile.objects
        .get_or_create(
            user=user
        )
    )

    return render(
        request,
        "User/checkout.html",
        {
            "user": user,
            "profile": profile,
            "cart": cart_obj,
            "items": items,
            "total": total
        }
    )


# =========================================================
# PLACE ORDER
# =========================================================

@login_required
@require_POST
def place_order(request):

    user = request.current_user

    # =====================================================
    # VALIDATE CUSTOMER DETAILS
    # =====================================================

    name = (
        request.POST.get(
            "name",
            ""
        ).strip()
    )

    phone = (
        request.POST.get(
            "phone",
            ""
        ).strip()
    )

    address = (
        request.POST.get(
            "address",
            ""
        ).strip()
    )

    city = (
        request.POST.get(
            "city",
            ""
        ).strip()
    )

    pincode = (
        request.POST.get(
            "pincode",
            ""
        ).strip()
    )

    if not validate_name(name):

        messages.error(
            request,
            "Please enter a valid name."
        )

        return redirect(
            "checkout"
        )

    if not validate_phone(phone):

        messages.error(
            request,
            "Enter a valid 10-digit phone number."
        )

        return redirect(
            "checkout"
        )

    if not validate_address(address):

        messages.error(
            request,
            "Please enter a valid address."
        )

        return redirect(
            "checkout"
        )

    if not validate_city(city):

        messages.error(
            request,
            "Please enter a valid city."
        )

        return redirect(
            "checkout"
        )

    if not validate_pincode(pincode):

        messages.error(
            request,
            "Enter a valid 6-digit pincode."
        )

        return redirect(
            "checkout"
        )

    # =====================================================
    # TRANSACTION
    # =====================================================

    with transaction.atomic():

        # -------------------------------------------------
        # Lock cart
        # -------------------------------------------------

        cart_obj = (
            Cart.objects
            .select_for_update()
            .filter(
                user=user
            )
            .first()
        )

        if not cart_obj:

            messages.warning(
                request,
                "Your cart is empty."
            )

            return redirect(
                "cart"
            )

        # -------------------------------------------------
        # Reload cart items
        # -------------------------------------------------

        items = list(
            cart_obj.items
            .select_related("product")
            .all()
        )

        if not items:

            messages.warning(
                request,
                "Your cart is empty."
            )

            return redirect(
                "cart"
            )

        # -------------------------------------------------
        # Calculate total from database
        # -------------------------------------------------

        total = Decimal("0.00")

        for item in items:

            if (
                item.quantity < 1
                or item.quantity > MAX_CART_QUANTITY
            ):

                messages.error(
                    request,
                    "Invalid cart quantity."
                )

                return redirect(
                    "cart"
                )

            total += (
                item.product.price
                *
                item.quantity
            )

        # =================================================
        # CREATE ORDER
        # =================================================

        order = Order.objects.create(
            user=user,
            total=total,
            status="Pending",
            name=name,
            phone=phone,
            address=address,
            city=city,
            pincode=pincode
        )

        # =================================================
        # CREATE ORDER ITEMS
        # =================================================

        for item in items:

            product = item.product

            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                price=product.price,
                quantity=item.quantity
            )

        # =================================================
        # CLEAR CART
        # =================================================

        cart_obj.items.all().delete()

    messages.success(
        request,
        "Order placed successfully."
    )

    return redirect(
        "order_success",
        pk=order.id
    )


# =========================================================
# ORDER SUCCESS
# =========================================================

@login_required
def order_success(request, pk):

    user = request.current_user

    order_id = validate_positive_id(
        pk
    )

    if not order_id:

        messages.error(
            request,
            "Invalid order."
        )

        return redirect(
            "orders"
        )

    # =====================================================
    # OBJECT LEVEL AUTHORIZATION
    # =====================================================

    order = get_object_or_404(
        Order,
        id=order_id,
        user=user
    )

    return render(
        request,
        "User/order_success.html",
        {
            "user": user,
            "order": order
        }
    )


# =========================================================
# MY ORDERS
# =========================================================

@login_required
def orders(request):

    user = request.current_user

    order_list = (
        Order.objects
        .filter(
            user=user
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "User/orders.html",
        {
            "user": user,
            "orders": order_list
        }
    )


# =========================================================
# LOGOUT
# =========================================================

@never_cache
def logout(request):

    # =====================================================
    # COMPLETELY DESTROY SESSION
    # =====================================================

    request.session.flush()

    # =====================================================
    # EXTRA NO-CACHE HEADERS
    # =====================================================

    response = redirect(
        "login"
    )

    response["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, "
        "max-age=0, private"
    )

    response["Pragma"] = "no-cache"

    response["Expires"] = "0"

    return response