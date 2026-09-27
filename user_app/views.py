from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth import logout as django_logout
from django.contrib import messages
from django.contrib.auth.models import User
import re
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from .models import Userinfo, Testimonial, ContactMessage
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required

def home(request):
    testimonials = Testimonial.objects.filter(is_active=True).order_by('-created_at')[:3]
    return render(request, 'index.html', {'testimonials': testimonials})

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            # Check if Userinfo exists
            user_info = Userinfo.objects.get(email=email)
            # Authenticate using the underlying User model credentials
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                auth_login(request, user)
                # Keep user_id in session for legacy views if any
                request.session['user_id'] = user_info.id 
                messages.success(request, f"Welcome back, {user_info.first_name}!")
                return redirect('user_app:user_dashboard')
            else:
                messages.error(request, "Invalid email or password.")
        except Userinfo.DoesNotExist:
            messages.error(request, "Invalid email or password.")

    return render(request, 'login.html')


def logout_view(request):
    django_logout(request)
    return redirect('user_app:login') 


def register(request):
    if request.method == "POST":
        try:
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip()
            phone = request.POST.get("phone", "").strip()
            # membership_type = request.POST.get("membership_type")
            password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")

            email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"#check email and phone is valid
            phone_regex = r"^\+?\d{10,15}$"
            strong_password_regex = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
            if len(username) < 3:
                messages.error(request, "Full Name must be at least 3 characters long.")
                return redirect("user_app:register")
            if not re.match(email_regex, email):
                messages.error(request, "Enter a valid email address.")
                return redirect("user_app:register")
            if Userinfo.objects.filter(email=email).exists():
                messages.error(request, "This email is already registered.")
                return redirect("user_app:register")
            if phone and not re.match(phone_regex, phone):
                messages.error(request, "Enter a valid phone number.")
                return redirect("user_app:register")
            # if not membership_type:
            #     messages.error(request, "Please select a Membership Type.")
            #     return redirect("user_app:register")

            if not re.match(strong_password_regex, password):
                messages.error(request, "Password must be at least 8 characters long, include uppercase, lowercase, a number, and a symbol.")
                return redirect("user_app:register")

            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect("user_app:register")

            # Create User
            user = Userinfo.objects.create_user(username=email, email=email, password=password)
            user.first_name = username  # Storing full name
            user.phone = phone # Save phone number
            user.save()

            messages.success(request, "Account created successfully! You can now log in.")
            return redirect("user_app:login")

        except IntegrityError:
            messages.error(request, "A user with this email already exists.")
            return redirect("user_app:register")

        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect("user_app:register")

    return render(request, "register.html")


def pricing(request):
    return render(request, "pricing.html")


def try_free(request):
    return render(request, "try_free.html")


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        ContactMessage.objects.create(name=name, email=email, message=message)
        
        messages.success(request, "our team will contact you ,Tank you")
        return redirect('user_app:contact')
    return render(request, "contact.html")


def features(request):
    return render(request, "features.html")


def terms(request):
    return render(request, "terms.html")


def privacy_policy(request):
    return render(request, "privacy_policy.html")


@login_required(login_url='user_app:login')
def user_profile(request):
    # Using request.user directly since it's already a Userinfo instance
    return render(request, "user_profile.html", {"user": request.user})


def settings(request):
    user = request.user
    # You can pass the user's payments and membership type here
    return render(request, "settings.html", {'user': user})


from .forms import FeedbackForm

def feedback(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback_instance = form.save(commit=False)
            if request.user.is_authenticated:
                feedback_instance.user = request.user
            feedback_instance.save()
            messages.success(request, "Thank you for your feedback!")
            return redirect('user_app:feedback')
        else:
            pass # form.errors will handle it
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {'email': request.user.email, 'name': request.user.get_full_name() or request.user.username}
        form = FeedbackForm(initial=initial_data)

    return render(request, "feedback.html", {'form': form})



@login_required(login_url='user_app:login')
def history(request):
    from .models import ChatSession
    sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, "history.html", {"user": request.user, "sessions": sessions})


@login_required(login_url='user_app:login')
def user_dashboard(request):
    # Using request.user directly
    return render(request, "user_dashboard.html", {"user": request.user})


def edit_profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_app:login')

    try:
        user = Userinfo.objects.get(id=user_id)
    except Userinfo.DoesNotExist:
        return redirect('user_app:login')

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        # membership_type usually shouldn't be editable by user directly unless it's just a display or specific update logic
        # keeping it for now as per original code
        user.membership_type = request.POST.get('membership_type', user.membership_type) 
        
        try:
            user.save()
            messages.success(request, "Profile updated successfully!")
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")
            
        return redirect('user_app:user_profile')
    
    return render(request, 'edit_profile.html', {'user': user})