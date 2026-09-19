import re
from functools import wraps

from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import Register


# ============================================================
# SECURITY / VALIDATION SETTINGS
# ============================================================

SESSION_TIMEOUT = 7200

MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 128
MIN_PASSWORD_LENGTH = 8


# ============================================================
# PASSWORD VALIDATION
# ============================================================

def validate_password_strength(password):
    """
    Password requirements:

    Minimum 8 characters
    Maximum 128 characters
    At least one uppercase letter
    At least one lowercase letter
    At least one number
    """

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, (
            "Password must contain at least 8 characters, "
            "one uppercase letter, one lowercase letter, "
            "and one number."
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        return False, (
            f"Password cannot exceed "
            f"{MAX_PASSWORD_LENGTH} characters."
        )

    if not re.search(r"[A-Z]", password):
        return False, (
            "Password must contain at least one uppercase letter."
        )

    if not re.search(r"[a-z]", password):
        return False, (
            "Password must contain at least one lowercase letter."
        )

    if not re.search(r"\d", password):
        return False, (
            "Password must contain at least one number."
        )

    return True, ""


# ============================================================
# EMAIL VALIDATION
# ============================================================

def validate_user_email(email):
    """
    Validate email format and length.
    """

    if not email:
        return False

    if len(email) > MAX_EMAIL_LENGTH:
        return False

    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


# ============================================================
# SESSION AUTHENTICATION
# ============================================================

def get_authenticated_user(request):
    """
    Return the currently logged-in Register object.

    Returns None if:
    - user_id is not present
    - user does not exist
    - account is not approved
    """

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    try:

        user = Register.objects.get(id=user_id)

    except Register.DoesNotExist:

        request.session.flush()

        return None

    # Only approved accounts can remain authenticated.
    if user.approval_status != "approved":

        request.session.flush()

        return None

    return user


# ============================================================
# LOGIN CHECK
# ============================================================

def is_authenticated(request):
    return get_authenticated_user(request) is not None


# ============================================================
# LOGIN REQUIRED DECORATOR
# ============================================================

def login_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user = get_authenticated_user(request)

        if user is None:

            messages.warning(
                request,
                "Please login to continue."
            )

            return redirect("login")

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# USER ROLE REQUIRED
# ============================================================

def user_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user = get_authenticated_user(request)

        if user is None:

            messages.warning(
                request,
                "Please login to continue."
            )

            return redirect("login")

        if user.role != "user":

            messages.error(
                request,
                "You do not have permission to access this page."
            )

            return redirect("index")

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# SHOP ROLE REQUIRED
# ============================================================

def shop_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user = get_authenticated_user(request)

        if user is None:

            messages.warning(
                request,
                "Please login to continue."
            )

            return redirect("login")

        if user.role != "shop":

            messages.error(
                request,
                "Shop account required."
            )

            return redirect("index")

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# ADMIN ROLE REQUIRED
# ============================================================

def admin_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user = get_authenticated_user(request)

        if user is None:

            messages.warning(
                request,
                "Please login to continue."
            )

            return redirect("login")

        if user.role != "admin":

            messages.error(
                request,
                "Admin access required."
            )

            return redirect("index")

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# HOME PAGE
# ============================================================

def index(request):
    """
    Public MiniShop home page.

    Anyone can access this page.
    """

    return render(
        request,
        "Guest/index.html"
    )


# ============================================================
# REGISTER
# ============================================================

def register(request):
    """
    User registration.

    Flow:

    Register form
        ↓
    Validate input
        ↓
    Check duplicate email
        ↓
    Hash password
        ↓
    Create Register account
        ↓
    Login automatically
        ↓
    Redirect to user home
    """

    # --------------------------------------------------------
    # Already logged in
    # --------------------------------------------------------

    existing_user = get_authenticated_user(request)

    if existing_user is not None:

        if existing_user.role == "shop":
            return redirect("shop_home")

        if existing_user.role == "admin":
            return redirect("admin_home")

        return redirect("user_home")


    # --------------------------------------------------------
    # Only process POST
    # --------------------------------------------------------

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )


        # ----------------------------------------------------
        # NAME VALIDATION
        # ----------------------------------------------------

        if not name:

            messages.error(
                request,
                "Name is required."
            )

            return render(
                request,
                "Guest/register.html"
            )


        if len(name) > MAX_NAME_LENGTH:

            messages.error(
                request,
                f"Name cannot exceed "
                f"{MAX_NAME_LENGTH} characters."
            )

            return render(
                request,
                "Guest/register.html"
            )


        # ----------------------------------------------------
        # EMAIL VALIDATION
        # ----------------------------------------------------

        if not validate_user_email(email):

            messages.error(
                request,
                "Please enter a valid email address."
            )

            return render(
                request,
                "Guest/register.html"
            )


        # ----------------------------------------------------
        # PASSWORD VALIDATION
        # ----------------------------------------------------

        valid_password, password_error = \
            validate_password_strength(password)

        if not valid_password:

            messages.error(
                request,
                password_error
            )

            return render(
                request,
                "Guest/register.html"
            )


        # ----------------------------------------------------
        # CONFIRM PASSWORD
        # ----------------------------------------------------

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match."
            )

            return render(
                request,
                "Guest/register.html"
            )


        # ----------------------------------------------------
        # DUPLICATE EMAIL
        # ----------------------------------------------------

        if Register.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return render(
                request,
                "Guest/register.html"
            )


        # ----------------------------------------------------
        # CREATE USER
        # ----------------------------------------------------

        try:

            user = Register.objects.create(
                name=name,
                email=email,
                password=make_password(password),
                role="user",
                approval_status="approved"
            )

        except Exception:

            messages.error(
                request,
                "Unable to create account. Please try again."
            )

            return render(
                request,
                "Guest/register.html"
            )


        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        request.session.flush()

        request.session["user_id"] = user.id
        request.session["user_name"] = user.name
        request.session["user_email"] = user.email
        request.session["user_role"] = user.role

        # Compatibility with older code
        request.session["role"] = user.role

        request.session.set_expiry(
            SESSION_TIMEOUT
        )

        messages.success(
            request,
            "Account created successfully."
        )

        return redirect("user_home")


    # --------------------------------------------------------
    # GET REQUEST
    # --------------------------------------------------------

    return render(
        request,
        "Guest/register.html"
    )


# ============================================================
# LOGIN
# ============================================================

def login(request):
    """
    Session-based login.
    """

    # --------------------------------------------------------
    # Already authenticated
    # --------------------------------------------------------

    existing_user = get_authenticated_user(request)

    if existing_user is not None:

        if existing_user.role == "shop":
            return redirect("shop_home")

        if existing_user.role == "admin":
            return redirect("admin_home")

        return redirect("user_home")


    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        password = request.POST.get(
            "password",
            ""
        )


        # ----------------------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------------------

        if not email or not password:

            messages.error(
                request,
                "Email and password are required."
            )

            return render(
                request,
                "Guest/login.html"
            )


        # ----------------------------------------------------
        # FIND USER
        # ----------------------------------------------------

        try:

            user = Register.objects.get(
                email__iexact=email
            )

        except Register.DoesNotExist:

            messages.error(
                request,
                "Invalid email or password."
            )

            return render(
                request,
                "Guest/login.html"
            )


        # ----------------------------------------------------
        # PASSWORD CHECK
        # ----------------------------------------------------

        if not check_password(
            password,
            user.password
        ):

            messages.error(
                request,
                "Invalid email or password."
            )

            return render(
                request,
                "Guest/login.html"
            )


        # ----------------------------------------------------
        # APPROVAL CHECK
        # ----------------------------------------------------

        if user.approval_status != "approved":

            messages.warning(
                request,
                "Your account is not approved yet."
            )

            return render(
                request,
                "Guest/login.html"
            )


        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        request.session.flush()

        request.session["user_id"] = user.id
        request.session["user_name"] = user.name
        request.session["user_email"] = user.email
        request.session["user_role"] = user.role

        # Compatibility with existing code
        request.session["role"] = user.role

        request.session.set_expiry(
            SESSION_TIMEOUT
        )


        # ----------------------------------------------------
        # ROLE REDIRECTION
        # ----------------------------------------------------

        if user.role == "shop":

            messages.success(
                request,
                f"Welcome back, {user.name}!"
            )

            return redirect("shop_home")


        if user.role == "admin":

            messages.success(
                request,
                f"Welcome back, {user.name}!"
            )

            return redirect("admin_home")


        messages.success(
            request,
            f"Welcome back, {user.name}!"
        )

        return redirect("user_home")


    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        "Guest/login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

def logout(request):
    """
    Logout the current user.

    POST is recommended for logout.
    """

    if request.method == "POST":

        request.session.flush()

        messages.success(
            request,
            "You have been logged out successfully."
        )

        return redirect("login")


    # Allow GET as a fallback for older links.
    request.session.flush()

    return redirect("login")