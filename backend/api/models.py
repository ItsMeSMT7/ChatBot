from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    profile_picture = models.URLField(blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

class UserChat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    messages = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']

class Titanic(models.Model):
    passenger_id = models.IntegerField(primary_key=True)
    survived = models.IntegerField()
    pclass = models.IntegerField()
    name = models.TextField()
    sex = models.TextField()
    age = models.FloatField(null=True)
    sibsp = models.IntegerField()
    parch = models.IntegerField()
    ticket = models.TextField()
    fare = models.FloatField()
    cabin = models.TextField(null=True)
    embarked = models.TextField(null=True)

    class Meta:
        db_table = 'titanic'
        managed = False

class StateData(models.Model):
    state = models.CharField(max_length=100)
    population = models.IntegerField()
    income = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.state
    
    class Meta:
        db_table = 'state_data'
