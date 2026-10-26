from django.db import models
from django.contrib.auth.models import User


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class PaymentOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"

    reference = models.CharField(max_length=32, unique=True)
    razorpay_order_id = models.CharField(max_length=64, unique=True)
    razorpay_payment_id = models.CharField(max_length=64, blank=True)
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="INR")
    items = models.JSONField()
    customer = models.JSONField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.reference


class Payment(models.Model):
    """A Razorpay payment belonging to a Django user."""

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    razorpay_order_id = models.CharField(max_length=64, unique=True)
    razorpay_payment_id = models.CharField(max_length=64, blank=True)
    amount = models.PositiveIntegerField(help_text="Amount in paise")
    status = models.CharField(
        max_length=7,
        choices=Status.choices,
        default=Status.CREATED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.razorpay_order_id


class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.PositiveIntegerField(help_text="Price in paise")
    image = models.URLField(blank=True)
    brand = models.CharField(max_length=100, blank=True)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Order(models.Model):
    product_name = models.CharField(max_length=200, blank=True)
    amount = models.PositiveIntegerField(help_text="Amount in paise")
    payment_method = models.CharField(max_length=20)
    payment_id = models.CharField(max_length=100, blank=True)
    customer_name = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=30, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name or 'Order'} - {self.amount}"
