from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from .models import Airport, Flight, Passenger, Ticket
from decimal import Decimal
from django.contrib import messages
from datetime import datetime
from .forms import UpdateUserForm, CustomPasswordChangeForm
from django.contrib.auth.models import User
from .forms import BootstrapUserCreationForm
from .forms import BootstrapAuthenticationForm
from io import BytesIO
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import qrcode
import tempfile
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
import random
import string, calendar


# register for a new account
def register(request):
    if request.method == 'POST':
        form = BootstrapUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
    else:
        form = BootstrapUserCreationForm()
    return render(request, 'reservations/register.html', {'form': form})


# login page
def login_view(request):
    if request.method == 'POST':
        form = BootstrapAuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                form.add_error(None, 'Invalid username or password.')
    else:
        form = BootstrapAuthenticationForm()
    return render(request, 'reservations/login.html', {'form': form})

# logout page
@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

# home page
@login_required
def home(request):
    return render(request, 'reservations/home.html')

# welcome page
@login_required
def welcome(request):
    return render(request, 'reservations/welcome.html')

# account profile page
@login_required
def my_account(request):
    return render(request, 'reservations/my_account.html')

# searching flights to book page. User enters depature and arrival location, date, and number of tickets.
@login_required
def search(request):

    if request.method == 'POST':
        #on post we request the airports and date, 
        depart_airport_code = request.POST['depart_airport']
        arrival_airport_code = request.POST['arrival_airport']
        departure_date = request.POST['depart']
    
        return_date = request.POST.get('return', None) #set to none in case it is one way flight
        
        tickets = request.POST['tickets']

        if depart_airport_code == arrival_airport_code:
            error_message = "Invalid destination. Please select a different airport."
            airports = Airport.objects.all()
            return render(request, 'reservations/search.html', {'airports': airports, 'error_message': error_message})
        
        
        #we redirect the user to the list of flights based on the searh
        redirect_url = reverse('list_flights') + f'?depart_airport_code={depart_airport_code}&arrival_airport_code={arrival_airport_code}&departure_date={departure_date}&tickets={tickets}'
        if return_date:
            #in case the user did have a return date we include the date
           
            redirect_url += f'&return_date={return_date}'
        return redirect(redirect_url)
    else:
        #get all airport information and list all of the required information for the search form
        error_message = request.session.pop('error_message', None)
        airports = Airport.objects.all()
        return render(request, 'reservations/search.html', {'airports': airports, 'error_message': error_message})
    
# generates all the flights filtered based on a search
@login_required
def list_flights(request):
    #function to list flights
    if request.method == 'POST':
        depart_flight_id = request.POST['depart_flights[]']
        return_flight_id = request.POST.get('return_flights[]', None)
        tickets = request.GET.get('tickets')
        
        redirect_url = reverse('passenger_info_view', args=[int(tickets)]) + f'?depart_flight_id={depart_flight_id}'
        if return_flight_id:
            redirect_url += f'&return_flight_id={return_flight_id}'
        
        return redirect(redirect_url)
    else:
        depart_airport_code = request.GET.get('depart_airport_code')
        arrival_airport_code = request.GET.get('arrival_airport_code')
        departure_date_str = request.GET.get('departure_date')
        ret_date_str = request.GET.get('return_date')
        
        depart_airport = Airport.objects.get(code=depart_airport_code)
        arrival_airport = Airport.objects.get(code=arrival_airport_code)

        departure_date = datetime.strptime(departure_date_str, '%Y-%m-%d').date()
        showCalendar = request.GET.get('myCheckbox')

        flights = Flight.objects.filter(
            depart_airport=depart_airport,
            arrival_airport=arrival_airport,
        )

        if ret_date_str:
            return_date = datetime.strptime(ret_date_str, "%Y-%m-%d").date()
            return_flights = Flight.objects.filter(
                
                depart_airport=arrival_airport,
                arrival_airport=depart_airport,
                
            )
            
            # for a round-trip flight
            return render(request, 'reservations/flights_list.html', {'flights': flights, 'departure_date': departure_date, 'return_flights': return_flights, 'return_date': return_date})
        else:
            # for a one way flight
            return_flights = None

            return render(request, 'reservations/flights_list.html', {'flights': flights, 'departure_date': departure_date})

# changes the flight price based on the seat tier class the user chooses
def updatePriceForSeatClass(aFlight, seatClass):
        if seatClass == "Economy":
            aFlight.price = aFlight.economy_fare

        elif seatClass == "Business":
            aFlight.price = aFlight.business_fare

        else:
            aFlight.price = aFlight.first_fare

        return aFlight.price

def calculate_total_cost(depart_flight, return_flight, num_passengers):
    #Calculates the total cost of a ticket based on the flights and number of passengers.
    
    total_cost = Decimal(0)
    
    # Add the cost of the depart flight
    total_cost += Decimal(depart_flight.price + 177.5)
    
    
    # Add the cost of the return flight (if there is one)
    if return_flight:
        total_cost += Decimal(return_flight.price + 177.5)
    
    # Multiply the total cost by the number of passengers
    total_cost *= num_passengers
    '''security fee 12.00
    one time carry on fee 25.00
    transportation tax 40.50
    carrier imposed fees 100.00'''
    
    return total_cost

# creates a 6 alphanumeric character confirmation code
def generateConfirmationCode():
    confirmCode = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return confirmCode
     
@login_required
def passenger_info_view(request, num_tickets):
    if request.method == 'POST':
        depart_flight_id = request.GET.get('depart_flight_id')
        return_flight_id = request.GET.get('return_flight_id')
        
        depart_flight = Flight.objects.get(id=depart_flight_id)
        
        return_flight = Flight.objects.get(id=return_flight_id) if return_flight_id else None

        total_cost = calculate_total_cost(depart_flight, return_flight, num_tickets)
        confirmationCode = generateConfirmationCode()
        print("Here is your confirmation code:" + confirmationCode)
        ticket = Ticket.objects.create(user=request.user, depart_flight=depart_flight, return_flight=return_flight, total_cost=total_cost)

        for i in range(1, num_tickets+1):
            first_name = request.POST.get(f'first_name{i}')
            last_name = request.POST.get(f'last_name{i}')
            email = request.POST.get(f'email{i}')
            dob = request.POST.get(f'dob{i}')
            passenger = Passenger.objects.create(first_name=first_name, last_name=last_name, email=email, dob=dob)
            print(f"Creating passenger with first name: {first_name}, last name: {last_name}, email: {email}, dob: {dob}")
            ticket.passengers.add(passenger)
            
        redirect_url = reverse('payment_view', kwargs={'ticket_id': ticket.id})
        return redirect(redirect_url)
    else:
        ticket_range = range(1, num_tickets + 1)
        user_profile = request.user.profile
        user_dob = user_profile.birthdate.strftime('%Y-%m-%d') if user_profile.birthdate else ''
        return render(request, 'reservations/passenger_information.html', {'ticket_range': ticket_range, 'user_dob': user_dob})

# checkout page with a ticket summary of the flight and total cost
@login_required
def payment_view(request, ticket_id):
    ticket = Ticket.objects.get(id=ticket_id)
    if request.method == 'POST':
        card_number = request.POST['card_number']
        expiration_date = request.POST['expiration_date']
        cvv = request.POST['cvv']
        name = request.POST['name']
        address = request.POST['address']
        
        # update ticket as paid
        ticket.paid = True
        ticket.save()
        
        # Generate PDF and send as email attachment
        qr_code = qrcode.make(ticket.id)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            qr_code.save(tmp.name)
            pdf_data = generate_ticket_pdf(ticket, tmp.name)

        email_subject = 'Your Ticket Summary'
        email_body = render_to_string('reservations/email_body.html', {'ticket': ticket})
        email = EmailMessage(email_subject, email_body, 'noreply@northwest.com', [request.user.email])
        email.attach(f'ticket_{ticket.id}.pdf', pdf_data, 'application/pdf')
        email.send()

        return redirect('manage_reservations')
    
    else:
        passengers = ticket.passengers.all()
        return render(request, 'reservations/payment.html', {'ticket': ticket, 'passengers': passengers})

# creates a pdf of the ticket reservation order with a qr code.
def generate_ticket_pdf(ticket, qr_code_path):
    buffer = BytesIO()
    
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, "Northwest Airlines")
    p.drawString(100, 700, "Ticket Summary")
    p.drawString(100, 650, f"Ticket ID: {ticket.id}")
    p.drawString(100, 600, f"Passenger Name: {ticket.passengers.first().first_name} {ticket.passengers.first().last_name}")
    p.drawString(100, 550, f"Departure Date: {ticket.depart_flight.depart_time}")

    p.drawString(100, 500, f"Arrival Date: {ticket.depart_flight.arrival_time}")
    p.drawString(100, 450, f"Total Cost: {ticket.total_cost}")
    p.drawImage(qr_code_path, 400, 200, width=2*inch, height=2*inch)
    p.showPage()
    p.save()
    buffer.seek(0)
    pdf_data = buffer.getvalue()
    return pdf_data

# Allows a user to manage their flight reservations
@login_required
def manage_reservations(request):
    user_tickets = Ticket.objects.filter(user=request.user, paid=True)
    return render(request, 'reservations/manage_reservations.html', {'tickets': user_tickets})

@login_required
def cancel_reservation(request, ticket_id):
    ticket = Ticket.objects.get(id=ticket_id)

    # Ensure the ticket belongs to the requesting user
    if ticket.user != request.user:
        return HttpResponseForbidden("You do not have permission to cancel this reservation.")

    # Delete the ticket and all related passengers
    ticket.passengers.all().delete()
    ticket.delete()

    messages.success(request, 'Your reservation has been successfully canceled.')
    return redirect('manage_reservations')

# Allows a passenger to cancel their reservation flight
@login_required
def cancel_passenger(request, ticket_id, passenger_id):
    ticket = Ticket.objects.get(id=ticket_id)

    # Ensure the ticket belongs to the requesting user
    if ticket.user != request.user:
        return HttpResponseForbidden("You do not have permission to cancel this reservation.")

    passenger = Passenger.objects.get(id=passenger_id)

    
    # Remove the passenger from the ticket's passengers list
    ticket.passengers.remove(passenger)
    

    messages.success(request, 'Passenger has been successfully removed from the ticket.')
    return redirect('manage_reservations')

    
# Update user information page
@login_required
def update_user(request):
    if request.method == 'POST':
        form = UpdateUserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('my_account')
    else:
        form = UpdateUserForm(instance=request.user)
        form.fields['first_name'].initial = request.user.first_name
        form.fields['last_name'].initial = request.user.last_name
        form.fields['email'].initial = request.user.email
        form.fields['birthdate'].initial = request.user.profile.birthdate
        form.fields['street_address'].initial = request.user.profile.street_address
        form.fields['zip_code'].initial = request.user.profile.zip_code
        form.fields['state'].initial = request.user.profile.state

    return render(request, 'reservations/update_user.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Your password has been updated.')
            return redirect('my_account')
        else:
            messages.error(request, 'Please correct the error(s) below.')
    else:
        form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'reservations/change_password.html', {'form': form})

def createCalendar(year, month):
    cal = calendar.monthcalendar(year,month)
    monthStringArray = []
    for week in cal:
        # Formatting each day in a week
        formatted_week = [str(day) if day != 0 else ' ' for day in week]

        monthStringArray.extend(formatted_week)
        monthStringArray.extend(',')
    return monthStringArray

@login_required
def showCalendarMonth(request, year, month):
    date = datetime(year, month, 1)
    monthName = date.strftime("%B")
    calendarMonth = createCalendar(year,month)
    print(calendarMonth)
    return render(request, 'reservations/calendar.html', {'calendarMonth':calendarMonth, 'year': year, 'monthName': monthName})
