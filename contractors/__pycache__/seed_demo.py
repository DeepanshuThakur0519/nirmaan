from decimal import Decimal

from django.contrib.auth.models import User

from contractors.models import ContractorProfile, Specialty

names = ["Residential", "Commercial", "Warehouse", "Renovation", "Interiors"]
spec = {n: Specialty.objects.get_or_create(name=n)[0] for n in names}

demo = [
    ("demo_one", "Demo Arch Builders", "Jaipur", 12, 2000000, 15000000, ["Residential", "Interiors"]),
    ("demo_two", "Demo Skyline Constructions", "Mumbai", 18, 10000000, 90000000, ["Commercial", "Warehouse"]),
    ("demo_three", "Demo Renovate Right", "Pune", 6, 500000, 4000000, ["Renovation", "Interiors"]),
    ("demo_four", "Demo Stonework & Sons", "Lucknow", 25, 3000000, 40000000, ["Residential", "Commercial"]),
    ("demo_five", "Demo Metro Warehousing Co", "Bengaluru", 9, 8000000, 60000000, ["Warehouse"]),
]

for username, company, city, exp, low, high, specs in demo:
    user, _ = User.objects.get_or_create(username=username)
    profile, _ = ContractorProfile.objects.get_or_create(
        user=user,
        defaults=dict(
            company_name=company,
            city=city,
            about="Sample profile used only for testing the Nirmaan search filters.",
            experience_years=exp,
            min_budget=Decimal(low),
            max_budget=Decimal(high),
            verified=True,
        ),
    )
    profile.specialties.set([spec[s] for s in specs])

print("Done. Contractors in database:", ContractorProfile.objects.count())