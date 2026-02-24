from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import Kit, PostMortem


def home(request):
    return render(request, 'core/home.html') #public homepage

# Create your views here.
@login_required
def dashboard(request):
    kits = Kit.objects.all()
    recent_postmortems = PostMortem.objects.order_by('-created_at')[:10]

    return render(request, 'core/dashboard.html', {
        "kits": kits,
        'recent_postmortems': recent_postmortems})


def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)  # <-- needs the user
            return redirect("dashboard")  # change if your dashboard name differs
        else:
            messages.error(request, "Invalid username or password.")

    # GET (or failed POST) just shows the form
    return render(request, "core/login.html")


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)             # log in right after signup
            return redirect('dashboard')     # go straight to dashboard
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})


@login_required
def postmortem(request, pk):
    pm = get_object_or_404(PostMortem, pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "acknowledge":
            pm.status = "Acknowledged"  # adjust to your model
            pm.save()
            return redirect("postmortem", pk=pm.pk)  # redirect after POST

    # Always return a response on GET (and after any redirect)
    return render(request, "core/post_mortem.html", {"pm": pm})