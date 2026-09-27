from django import forms
from .models import Feedback

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'rating', 'review']
        widgets = {
            'rating': forms.RadioSelect(),
            'review': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Your Message', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'placeholder': 'Your Name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your Email', 'class': 'form-control'}),
        }
