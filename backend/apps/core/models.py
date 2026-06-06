import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.postgres.search import SearchVectorField

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]

PROCESSING_STATUS = [
    ("pending", "Pending"),
    ("processing", "Processing"),
    ("completed", "Completed"),
    ("failed", "Failed"),
]


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.is_superuser or (self.role and self.role.name == "Admin")


class Topic(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="topics")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="categories")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        unique_together = ("topic", "name")
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.topic.name} → {self.name}"


class SubCategory(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="subcategories")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.name} → {self.name}"


class Question(TimeStampedModel):
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="questions")
    title = models.TextField()
    normalized_title = models.TextField(blank=True, null=True)
    search_vector = SearchVectorField(null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="questions")
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["normalized_title"])]

    def __str__(self):
        return self.title[:80]


class Answer(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    content = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="answers")
    upvotes = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.content[:50]


class AnswerPoint(TimeStampedModel):
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="points")
    point = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="answer_points")

    def __str__(self):
        return self.point[:50]


class PDFUpload(TimeStampedModel):
    file = models.FileField(upload_to="pdfs/")
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="uploads")
    process_status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default="pending")
    processing_report = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.uploaded_by.email} — {self.process_status}"


class ApprovalQueue(TimeStampedModel):
    OBJECT_TYPES = [
        ("topic", "Topic"),
        ("category", "Category"),
        ("subcategory", "SubCategory"),
    ]
    object_type = models.CharField(max_length=50, choices=OBJECT_TYPES)
    object_id = models.UUIDField()
    requested_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="approval_requests")
    is_approved = models.BooleanField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reviews"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.object_type} — {self.requested_by.email}"


class Notification(TimeStampedModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} — {self.title}"


class AuditLog(TimeStampedModel):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=255)
    object_type = models.CharField(max_length=255)
    object_id = models.UUIDField()
    previous_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} — {self.object_type} — {self.user}"