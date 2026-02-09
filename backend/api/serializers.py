from rest_framework import serializers #drf
from .models import StateData

class StateDataSerializer(serializers.ModelSerializer):
    #get all data using api
    class Meta:
        model = StateData
        fields = '__all__'
