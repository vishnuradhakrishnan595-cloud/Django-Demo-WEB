import re
import secrets
from datetime import datetime, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
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

# OTP settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


# ============================================================
# VALIDATION HELPERS
# ============================================================

def validate_name(name):
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
# OTP HELPERS
# ============================================================

def generate_otp():
    """
    Generate secure 6-digit OTP.
    """

    return f"{secrets.randbelow(1000000):06d}"


def send_otp_email(email, otp):
    """
    Send OTP verification email.
    """

    subject = "MiniShop - Email Verification OTP"

    message = f"""
Hello,

Thank you for registering with MiniShop.

Your email verification OTP is:

{otp}

This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.

If you did not create a MiniShop account, please ignore this email.

Regards,
MiniShop Team
"""

    send_mail(
        subject,
        message,
        None,
        [email],
        fail_silently=False,
    )


def clear_otp_session(request):
    """
    Remove temporary registration/OTP data.
    """

    otp_keys = [
        "registration_name",
        "registration_email",
        "registration_password",
        "registration_otp",
        "registration_otp_created",
        "registration_otp_attempts",
    ]

    for key in otp_keys:
        request.session.pop(key, None)


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
        user = Register.objects.get(id=user_id)

    except Register.DoesNotExist:
        request.session.flush()
        return None

    if user.approval_status != "approved":
        request.session.flush()
        return None

    return user


def is_authenticated(request):
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
        # Name
        # ----------------------------------------------------

        if not validate_name(name):

            messages.error(
                request,
                "Please enter a valid name."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Email
        # ----------------------------------------------------

        if not validate_email_address(email):

            messages.error(
                request,
                "Please enter a valid email address."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Password
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
        # Existing email
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
        # GENERATE OTP
        # ====================================================

        otp = generate_otp()

        # ----------------------------------------------------
        # Store temporary registration data
        # ----------------------------------------------------

        request.session["registration_name"] = name

        request.session["registration_email"] = email

        # Never store plain password
        request.session["registration_password"] = make_password(
            password
        )

        request.session["registration_otp"] = otp

        request.session["registration_otp_created"] = (
            timezone.now().isoformat()
        )

        request.session["registration_otp_attempts"] = 0

        # ----------------------------------------------------
        # Send OTP
        # ----------------------------------------------------

        try:

            send_otp_email(
                email,
                otp
            )

        except Exception as error:

            print("OTP EMAIL ERROR:", error)

            clear_otp_session(request)

            messages.error(
                request,
                "Unable to send verification email. "
                "Please try again later."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

        messages.success(
            request,
            "A 6-digit verification code has been sent to your email."
        )

        return redirect("verify_otp")

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        "Guest/register.html"
    )


# ============================================================
# VERIFY OTP
# ============================================================

def verify_otp(request):

    email = request.session.get(
        "registration_email"
    )

    if not email:

        messages.warning(
            request,
            "Your registration session has expired. "
            "Please register again."
        )

        return redirect("register")

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        entered_otp = request.POST.get(
            "otp",
            ""
        ).strip()

        # ----------------------------------------------------
        # Validate OTP format
        # ----------------------------------------------------

        if not re.fullmatch(
            r"\d{6}",
            entered_otp
        ):

            messages.error(
                request,
                "Please enter a valid 6-digit OTP."
            )

            return redirect("verify_otp")

        stored_otp = request.session.get(
            "registration_otp"
        )

        created_at_string = request.session.get(
            "registration_otp_created"
        )

        attempts = request.session.get(
            "registration_otp_attempts",
            0
        )

        # ----------------------------------------------------
        # Missing OTP
        # ----------------------------------------------------

        if not stored_otp or not created_at_string:

            clear_otp_session(request)

            messages.error(
                request,
                "Your OTP session has expired. "
                "Please register again."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Maximum attempts
        # ----------------------------------------------------

        if attempts >= MAX_OTP_ATTEMPTS:

            clear_otp_session(request)

            messages.error(
                request,
                "Too many incorrect OTP attempts. "
                "Please register again."
            )

            return redirect("register")

        # ----------------------------------------------------
        # OTP expiry
        # ----------------------------------------------------

        try:

            created_at = datetime.fromisoformat(
                created_at_string
            )

            if timezone.is_naive(created_at):

                created_at = timezone.make_aware(
                    created_at,
                    timezone.get_current_timezone()
                )

        except (ValueError, TypeError):

            clear_otp_session(request)

            messages.error(
                request,
                "Your OTP session is invalid. "
                "Please register again."
            )

            return redirect("register")

        expiry_time = (
            created_at
            + timedelta(
                minutes=OTP_EXPIRY_MINUTES
            )
        )

        if timezone.now() > expiry_time:

            clear_otp_session(request)

            messages.error(
                request,
                "Your OTP has expired. Please register again."
            )

            return redirect("register")

        # ====================================================
        # COMPARE OTP
        # ====================================================

        if not secrets.compare_digest(
            entered_otp,
            stored_otp
        ):

            attempts += 1

            request.session[
                "registration_otp_attempts"
            ] = attempts

            remaining_attempts = (
                MAX_OTP_ATTEMPTS - attempts
            )

            if remaining_attempts <= 0:

                clear_otp_session(request)

                messages.error(
                    request,
                    "Too many incorrect attempts. "
                    "Please register again."
                )

                return redirect("register")

            messages.error(
                request,
                f"Incorrect OTP. "
                f"{remaining_attempts} attempts remaining."
            )

            return redirect("verify_otp")

        # ====================================================
        # OTP VERIFIED
        # ====================================================

        name = request.session.get(
            "registration_name"
        )

        email = request.session.get(
            "registration_email"
        )

        password_hash = request.session.get(
            "registration_password"
        )

        # ----------------------------------------------------
        # Check registration data
        # ----------------------------------------------------

        if not name or not email or not password_hash:

            clear_otp_session(request)

            messages.error(
                request,
                "Registration data is incomplete. "
                "Please register again."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Check duplicate email again
        # ----------------------------------------------------

        if Register.objects.filter(
            email=email
        ).exists():

            clear_otp_session(request)

            messages.error(
                request,
                "An account with this email already exists."
            )

            return redirect("login")

        # ====================================================
        # CREATE ACCOUNT
        # ====================================================

        try:

            Register.objects.create(

                name=name,

                email=email,

                password=password_hash,

                role="user",

                approval_status="approved",

            )

        except Exception as error:

            print("ACCOUNT CREATION ERROR:", error)

            messages.error(
                request,
                "Unable to create your account. "
                "Please try again."
            )

            return redirect("register")

        # ----------------------------------------------------
        # Clear temporary OTP data
        # ----------------------------------------------------

        clear_otp_session(request)

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

        messages.success(
            request,
            "Email verified successfully. "
            "Your account has been created. Please login."
        )

        return redirect("login")

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        "Guest/verify_otp.html"
    )


# ============================================================
# RESEND OTP
# ============================================================

def resend_otp(request):

    # Only POST allowed
    if request.method != "POST":

        return redirect("verify_otp")

    # --------------------------------------------------------
    # Registration email
    # --------------------------------------------------------

    email = request.session.get(
        "registration_email"
    )

    if not email:

        messages.warning(
            request,
            "Your registration session has expired. "
            "Please register again."
        )

        return redirect("register")

    # --------------------------------------------------------
    # Check registration data
    # --------------------------------------------------------

    if not request.session.get(
        "registration_name"
    ) or not request.session.get(
        "registration_password"
    ):

        clear_otp_session(request)

        messages.warning(
            request,
            "Your registration session has expired. "
            "Please register again."
        )

        return redirect("register")

    # --------------------------------------------------------
    # Check existing account
    # --------------------------------------------------------

    if Register.objects.filter(
        email=email
    ).exists():

        clear_otp_session(request)

        messages.info(
            request,
            "An account with this email already exists."
        )

        return redirect("login")

    # ========================================================
    # GENERATE NEW OTP
    # ========================================================

    otp = generate_otp()

    request.session["registration_otp"] = otp

    request.session["registration_otp_created"] = (
        timezone.now().isoformat()
    )

    request.session["registration_otp_attempts"] = 0

    # --------------------------------------------------------
    # Send OTP
    # --------------------------------------------------------

    try:

        send_otp_email(
            email,
            otp
        )

    except Exception as error:

        print("RESEND OTP EMAIL ERROR:", error)

        messages.error(
            request,
            "Unable to send a new OTP. "
            "Please try again later."
        )

        return redirect("verify_otp")

    messages.success(
        request,
        "A new OTP has been sent to your email."
    )

    return redirect("verify_otp")


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
        # Validation
        # ----------------------------------------------------

        if not validate_email_address(email):

            messages.error(
                request,
                "Invalid email or password."
            )

            return redirect("login")

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

            # Prevent session fixation
            request.session.flush()

            request.session["user_id"] = user.id

            request.session["user_name"] = user.name

            request.session["user_email"] = user.email

            request.session["user_role"] = user.role

            # Compatibility
            request.session["role"] = user.role

            request.session.set_expiry(
                SESSION_TIMEOUT
            )

            return redirect("user_home")

        # ====================================================
        # SHOP
        # ====================================================

        elif user.role == "shop":

            if user.approval_status == "pending":

                messages.warning(
                    request,
                    "Your shop account is waiting "
                    "for admin approval."
                )

                return redirect("login")

            if user.approval_status == "rejected":

                messages.error(
                    request,
                    "Your shop account has been rejected."
                )

                return redirect("login")

            if user.approval_status == "approved":

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