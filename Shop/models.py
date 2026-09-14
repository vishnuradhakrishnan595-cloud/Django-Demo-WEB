from django.core.validators import (
    MaxValueValidator,
    MinValueValidator
)

from django.db import models

from Guest.models import Register


# =========================================================
# CATEGORY
# =========================================================

class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["name"]

    def __str__(self):

        return self.name


# =========================================================
# BRAND
# =========================================================

class Brand(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    logo = models.ImageField(
        upload_to="brands/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["name"]

    def __str__(self):

        return self.name


# =========================================================
# PRODUCT
# =========================================================

class Product(models.Model):

    shop = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        related_name="products"
    )

    name = models.CharField(
        max_length=200
    )

    description = models.TextField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )

    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["-created_at"]

    def __str__(self):

        return self.name


# =========================================================
# REVIEW
# =========================================================

class Review(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    # -----------------------------------------------------
    # Customer rating
    # -----------------------------------------------------

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    # -----------------------------------------------------
    # Customer comment
    # -----------------------------------------------------

    comment = models.TextField(
        blank=True
    )

    # -----------------------------------------------------
    # Shop reply
    # -----------------------------------------------------

    shop_reply = models.TextField(
        blank=True,
        default=""
    )

    # -----------------------------------------------------
    # Created date
    # -----------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["-created_at"]

        constraints = [

            # -------------------------------------------------
            # One review per customer per product
            # -------------------------------------------------

            models.UniqueConstraint(
                fields=[
                    "product",
                    "user"
                ],
                name="unique_product_user_review"
            )

        ]

    def __str__(self):

        return (
            f"{self.user.name} - "
            f"{self.product.name} - "
            f"{self.rating}★"
        )