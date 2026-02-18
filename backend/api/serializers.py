from rest_framework import serializers
from .models import StateData, User, Document, UserChat


# Existing serializer (keep this)
class StateDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StateData
        fields = '__all__'


# ⭐ ADD THIS (required for your views.py)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"