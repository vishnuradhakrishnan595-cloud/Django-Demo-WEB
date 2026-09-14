from django.db import models

from Guest.models import Register
from Shop.models import Product, Category, Brand


# =========================================================
# PROFILE
# =========================================================

class Profile(models.Model):

    user = models.OneToOneField(
        Register,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    image = models.ImageField(
        upload_to="profile/",
        blank=True,
        null=True
    )

    def __str__(self):

        return self.user.name


# =========================================================
# CART
# =========================================================

class Cart(models.Model):

    user = models.OneToOneField(
        Register,
        on_delete=models.CASCADE,
        related_name="cart"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.user.name}'s Cart"


# =========================================================
# CART ITEM
# =========================================================

class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    def __str__(self):

        return f"{self.product.name} - {self.quantity}"


# =========================================================
# ORDER
# =========================================================

class Order(models.Model):

    STATUS_CHOICES = [

        ("Pending", "Pending"),

        ("Accepted", "Accepted"),

        ("Rejected", "Rejected"),

        ("Shipped", "Shipped"),

        ("Delivered", "Delivered"),

        ("Cancelled", "Cancelled"),

    ]

    user = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    name = models.CharField(
        max_length=100
    )

    phone = models.CharField(
        max_length=20
    )

    address = models.TextField()

    city = models.CharField(
        max_length=100
    )

    pincode = models.CharField(
        max_length=10
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"Order #{self.id} - {self.user.name}"


# =========================================================
# ORDER ITEM
# =========================================================

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items"
    )

    product_name = models.CharField(
        max_length=200
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    @property
    def subtotal(self):

        return self.price * self.quantity

    def __str__(self):

        return f"{self.product_name} - {self.quantity}"