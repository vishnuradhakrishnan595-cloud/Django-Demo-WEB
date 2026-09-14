from django.test import TestCase, Client
from django.urls import reverse

from Guest.models import Register
from Shop.models import Product, Category, Brand, Review


class ShopReviewAccessTests(TestCase):

    def test_shop_can_view_reviews_for_its_products(self):
        shop = Register.objects.create(
            name="Shop Owner",
            email="shop@example.com",
            password="hashed-pass",
            role="shop",
            approval_status="approved",
        )

        customer = Register.objects.create(
            name="Customer User",
            email="customer@example.com",
            password="hashed-pass",
            role="user",
            approval_status="approved",
        )

        category = Category.objects.create(name="Electronics")
        brand = Brand.objects.create(name="MiniTech")
        product = Product.objects.create(
            shop=shop,
            name="Smart Watch",
            description="A smart watch",
            price="499.99",
            category=category,
            brand=brand,
        )

        Review.objects.create(
            product=product,
            user=customer,
            rating=5,
            comment="Great product and fast delivery.",
        )

        client = Client()
        session = client.session
        session["user_id"] = shop.id
        session.save()

        response = client.get(reverse("shop_reviews"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Great product and fast delivery.")
        self.assertContains(response, "Smart Watch")
        self.assertEqual(response.context["reviews"].count(), 1)
