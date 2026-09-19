import re
from functools import wraps

from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, redirect

from .models import Register


# ============================================================
# SECURITY / VALIDATION SETTINGS
# ============================================================

SESSION_TIMEOUT = 7200

MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 128


# ============================================================
# VALIDATION HELPERS
# ============================================================

def validate_name(name):
    """
    Validate user name.

    Requirements:
    - Minimum 2 characters
    - Maximum 100 characters
    - Only letters, spaces, dots, apostrophes and hyphens
    """

    if not name:
        return False

    name = name.strip()

    if len(name) < 2 or len(name) > MAX_NAME_LENGTH:
        return False

    return bool(
        re.fullmatch(
            r"^[A-Za-zÀ-ÿ .'-]+$",
            name
        )
    )


def validate_password(password):
    """
    Password requirements:
    - Minimum 8 characters
    - Maximum 128 characters
    - One uppercase letter
    - One lowercase letter
    - One number
    """

    if not password:
        return False

    if len(password) < 8 or len(password) > MAX_PASSWORD_LENGTH:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    return True


def validate_email_address(email):
    """
    Validate email address.
    """

    if not email:
        return False

    email = email.strip().lower()

    if len(email) > MAX_EMAIL_LENGTH:
        return False

    try:
        validate_email(email)
        return True

    except ValidationError:
        return False


# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def get_authenticated_user(request):
    """
    Get currently authenticated MiniShop user.
    """

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    try:
        user = Register.objects.get(
            id=user_id
        )

    except Register.DoesNotExist:

        request.session.flush()

        return None

    # User must be approved
    if user.approval_status != "approved":

        request.session.flush()

        return None

    return user


def is_authenticated(request):
    """
    Check whether the user is authenticated.
    """

    return get_authenticated_user(request) is not None


# ============================================================
# AUTHORIZATION DECORATORS
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

        request.current_user = user

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


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
                "You are not authorized to access this page."
            )

            return redirect("index")

        request.current_user = user

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


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
                "Only shop accounts can access this page."
            )

            return redirect("index")

        if user.approval_status != "approved":

            request.session.flush()

            messages.error(
                request,
                "Your shop account is not approved."
            )

            return redirect("login")

        request.current_user = user

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


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
                "Administrator access required."
            )

            return redirect("index")

        if user.approval_status != "approved":

            request.session.flush()

            messages.error(
                request,
                "Your administrator account is not approved."
            )

            return redirect("login")

        request.current_user = user

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# INDEX
# ============================================================

def index(request):

    return render(
        request,
        "Guest/index.html"
    )


# ============================================================
# REGISTER
# ============================================================

def register(request):

    # --------------------------------------------------------
    # Already logged in
    # --------------------------------------------------------

    current_user = get_authenticated_user(request)

    if current_user:

        if current_user.role == "user":

            return redirect("user_home")

        elif current_user.role == "shop":

            return redirect("shop_home")

        elif current_user.role == "admin":

            return redirect("admin_dashboard")

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        # ----------------------------------------------------
        # Get form data
        # ----------------------------------------------------

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
        # Validate name
        # ----------------------------------------------------

        if not validate_name(name):

            messages.error(
                request,
                "Please enter a valid name."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Validate email
        # ----------------------------------------------------

        if not validate_email_address(email):

            messages.error(
                request,
                "Please enter a valid email address."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Validate password
        # ----------------------------------------------------

        if not validate_password(password):

            messages.error(
                request,
                "Password must contain at least 8 characters, "
                "one uppercase letter, one lowercase letter, "
                "and one number."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Confirm password
        # ----------------------------------------------------

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Check existing email
        # ----------------------------------------------------

        if Register.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return redirect("register")

        # ====================================================
        # CREATE ACCOUNT
        # ====================================================

        try:

            Register.objects.create(

                name=name,

                email=email,

                # Store hashed password
                password=make_password(password),

                # Normal registration creates user account
                role="user",

                # User accounts are automatically approved
                approval_status="approved",

            )

        except Exception as error:

            print(
                "ACCOUNT CREATION ERROR:",
                error
            )

            messages.error(
                request,
                "Unable to create your account. "
                "Please try again."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Registration successful
        # ----------------------------------------------------

        messages.success(
            request,
            "Account created successfully. Please login."
        )

        return redirect("login")

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        "Guest/register.html"
    )


# ============================================================
# LOGIN
# ============================================================

def login(request):

    # --------------------------------------------------------
    # Already authenticated
    # --------------------------------------------------------

    current_user = get_authenticated_user(request)

    if current_user:

        if current_user.role == "user":

            return redirect("user_home")

        elif current_user.role == "shop":

            return redirect("shop_home")

        elif current_user.role == "admin":

            return redirect("admin_dashboard")

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
        # Validate email
        # ----------------------------------------------------

        if not validate_email_address(email):

            messages.error(
                request,
                "Invalid email or password."
            )

            return redirect("login")

        # ----------------------------------------------------
        # Validate password
        # ----------------------------------------------------

        if (
            not password
            or len(password) > MAX_PASSWORD_LENGTH
        ):

            messages.error(
                request,
                "Invalid email or password."
            )

            return redirect("login")

        # ----------------------------------------------------
        # Find account
        # ----------------------------------------------------

        user = Register.objects.filter(
            email=email
        ).first()

        # ----------------------------------------------------
        # Verify password
        # ----------------------------------------------------

        if (
            not user
            or not check_password(
                password,
                user.password
            )
        ):

            messages.error(
                request,
                "Invalid email or password."
            )

            return redirect("login")

        # ====================================================
        # NORMAL USER
        # ====================================================

        if user.role == "user":

            if user.approval_status != "approved":

                messages.error(
                    request,
                    "Your account is not approved."
                )

                return redirect("login")

            # ------------------------------------------------
            # Prevent session fixation
            # ------------------------------------------------

            request.session.flush()

            request.session["user_id"] = user.id

            request.session["user_name"] = user.name

            request.session["user_email"] = user.email

            request.session["user_role"] = user.role

            # Compatibility
            request.session["role"] = user.role

            # Session expires after 2 hours
            request.session.set_expiry(
                SESSION_TIMEOUT
            )

            return redirect("user_home")

        # ====================================================
        # SHOP
        # ====================================================

        elif user.role == "shop":

            # ------------------------------------------------
            # Pending shop
            # ------------------------------------------------

            if user.approval_status == "pending":

                messages.warning(
                    request,
                    "Your shop account is waiting "
                    "for admin approval."
                )

                return redirect("login")

            # ------------------------------------------------
            # Rejected shop
            # ------------------------------------------------

            if user.approval_status == "rejected":

                messages.error(
                    request,
                    "Your shop account has been rejected."
                )

                return redirect("login")

            # ------------------------------------------------
            # Approved shop
            # ------------------------------------------------

            if user.approval_status == "approved":

                # Prevent session fixation
                request.session.flush()

                request.session["user_id"] = user.id

                request.session["user_name"] = user.name

                request.session["user_email"] = user.email

                request.session["user_role"] = user.role

                request.session["role"] = user.role

                request.session.set_expiry(
                    SESSION_TIMEOUT
                )

                return redirect("shop_home")

            messages.error(
                request,
                "Unable to login to this account."
            )

            return redirect("login")

        # ====================================================
        # ADMIN
        # ====================================================

        elif user.role == "admin":

            messages.info(
                request,
                "Please use the Django Admin login "
                "for administrator access."
            )

            return redirect("login")

        # ====================================================
        # UNKNOWN ROLE
        # ====================================================

        messages.error(
            request,
            "Unable to login to this account."
        )

        return redirect("login")

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

    request.session.flush()

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect("index")