from django.urls import path

from .analytics_views import AnalyticsView, AnalyticsProgressView
from .views import ChatBotAPI, SignupAPI, LoginAPI, GoogleAuthAPI, UserChatsAPI


from . import views

urlpatterns = [
    path('chat/', ChatBotAPI.as_view()),
    path('signup/', SignupAPI.as_view()),
    path('login/', LoginAPI.as_view()),
    path('google-auth/', GoogleAuthAPI.as_view()),
    path('user-chats/', UserChatsAPI.as_view()),
      # ⭐ Admin APIs
    path('admin/stats/', views.admin_dashboard_stats, name='admin_stats'),
    path('admin/documents/', views.admin_documents, name='admin_documents'),
    path('admin/documents/<int:doc_id>/', views.admin_documents, name='admin_delete_document'),
   
    #Solven Analytics API
    path('analytics/analyze/', AnalyticsView.as_view(), name='analytics-analyze'),
    
    path('analytics/progress/', AnalyticsProgressView.as_view(), name='analytics-progress'),

]
