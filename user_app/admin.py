from django.contrib import admin
from .models import Userinfo

# Unregister default auth.User if it was accidentally tied to UserinfoAdmin
from django.contrib.auth.models import User
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

@admin.register(Userinfo)
class UserinfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'first_name', 'last_name', 'email', 'phone', 'password', 'date_joined', 'membership_type', 'attempt', 'is_active', 'view_search_history', 'edit_action')
    search_fields = ('username', 'email', 'phone')
    ordering = ('-date_joined',)
    
    def has_add_permission(self, request):
        return False

    def edit_action(self, obj):
        from django.urls import reverse
        from django.utils.html import mark_safe
        url = reverse('admin:user_app_userinfo_change', args=[obj.id])
        return mark_safe(f'<a href="{url}" style="background-color: var(--accent-color); color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-weight: 500;">Edit</a>')
    
    edit_action.short_description = 'Edit Details'

    readonly_fields = ('formatted_search_history', 'last_login', 'date_joined')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Membership', {'fields': ('membership_type', 'attempt')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
        ('Search History', {'fields': ('formatted_search_history',)}),
    )

    def view_search_history(self, obj):
        from django.utils.html import mark_safe
        if not obj.recent_searches:
            return "-"
        
        # Create a condensed version for the list view
        html = '<div style="max-height: 100px; overflow-y: auto; width: 300px;">'
        for search in obj.recent_searches:
            if isinstance(search, dict):
                prompt = search.get('prompt', '-')
                timestamp = search.get('timestamp', '')
                html += f'<div style="border-bottom: 1px solid #eee; padding: 2px;"><strong>{timestamp}</strong>: {prompt}</div>'
            else:
                html += f'<div style="border-bottom: 1px solid #eee; padding: 2px;">{str(search)}</div>'
        html += '</div>'
        return mark_safe(html)
    
    view_search_history.short_description = "Search History"

    def formatted_search_history(self, obj):
        from django.utils.html import mark_safe
        if not obj.recent_searches:
            return "No history."
        
        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr style="background:#f8f9fa; border-bottom:2px solid #dee2e6; text-align:left;">'
        html += '<th style="padding:8px; border:1px solid #ddd;">Timestamp</th>'
        html += '<th style="padding:8px; border:1px solid #ddd;">Prompt</th>'
        html += '<th style="padding:8px; border:1px solid #ddd;">Answer</th></tr>'
        
        for search in obj.recent_searches:
            if isinstance(search, dict):
                timestamp = search.get('timestamp', '-')
                prompt = search.get('prompt', '-')
                answer = search.get('answer', '-')[:100] + '...' if len(search.get('answer', '')) > 100 else search.get('answer', '-')
            else:
                # Fallback for old string data
                timestamp = '-'
                prompt = str(search)
                answer = '-'
                
            html += f'<tr><td style="padding:8px; border:1px solid #ddd;">{timestamp}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{prompt}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{answer}</td></tr>'
            
        html += '</table>'
        return mark_safe(html)
    
    formatted_search_history.short_description = "Recent Search History"

from .models import Feedback, Payment, SearchHistory, ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'message', 'created_at')
    search_fields = ('name', 'email')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'email', 'rating', 'review', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('review', 'name', 'email', 'user__username')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'plan', 'payment_date')
    list_filter = ('status', 'plan', 'payment_date')
    search_fields = ('user__username', 'transaction_id', 'order_id')
    readonly_fields = ('payment_date',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

# Unregister Group
from django.contrib.auth.models import Group
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

