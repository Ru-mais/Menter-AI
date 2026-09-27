from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.contrib.auth.hashers import make_password, check_password

PLAN_ATTEMPTS = {
    "basic": 5, 
    "pro": 10,   
    "premium": 50  
}
class Userinfo(AbstractUser):
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True) 
    email = models.EmailField(max_length=50, unique=True, null=True, blank=True)
    recent_searches = models.JSONField(null=True, blank=True, help_text="Stores recent searches for AI suggestions.")
    attempt = models.IntegerField(null=True, blank=True)
    username = models.CharField(max_length=40, unique=True, null=True, blank=True)

    membership_type = models.CharField(
        max_length=20, 
        null=True, 
        blank=True
    )
    
    registration_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    last_login = models.DateTimeField(auto_now=True, null=True, blank=True)

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",  # Provide unique related_name for groups
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions_set",  # Provide unique related_name for permissions
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )
    def save(self, *args, **kwargs):
        if self.membership_type and (self.attempt is None or self.attempt == 0):
            self.attempt = PLAN_ATTEMPTS.get(self.membership_type, 0)
        super().save(*args, **kwargs)


class Payment(models.Model):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]
    
    BASIC = 'basic'
    PRO = 'pro'
    PREMIUM = 'premium'
    
    PLAN_CHOICES = [
        (BASIC, 'Basic'),
        (PRO, 'Pro'),
        (PREMIUM, 'Premium'),
    ]
    
    PLAN_PRICES = {
        BASIC: 499,
        PRO: 999,
        PREMIUM: 1499
    }

    user = models.ForeignKey('Userinfo', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    method = models.CharField(max_length=20, default='card')
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default=BASIC)

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount} - {self.status} - {self.plan}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == self.COMPLETED:
            plan_type = self.plan
            if plan_type in PLAN_ATTEMPTS:
                self.user.membership_type = plan_type
                self.user.attempt = PLAN_ATTEMPTS[plan_type]
                self.user.save()



class Feedback(models.Model):
    user = models.ForeignKey('Userinfo', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Rating from 1 to 5")
    review = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.name or self.user.username} - {self.rating} Stars"


class SearchHistory(models.Model):
    user = models.ForeignKey('Userinfo', on_delete=models.CASCADE, related_name='search_history')
    prompt = models.TextField()
    answer = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Search Histories"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.prompt[:30]}..."


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=100, default="Virtue Mentor")
    contact_email = models.EmailField(default="support@virtuementor.com")
    contact_phone = models.CharField(max_length=20, default="+91 98765 43210")
    contact_address = models.TextField(default="123 AI Street, Tech City")
    
    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteSetting.objects.exists():
            return SiteSetting.objects.first()
        return super(SiteSetting, self).save(*args, **kwargs)


class Testimonial(models.Model):
    author_name = models.CharField(max_length=100)
    content = models.TextField()
    role = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Student, Developer")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author_name} - {self.role or 'User'}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.email}"
