from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from shs_system.models import SchoolInformation
from .models import Subscription, Plan


@receiver(post_save, sender=SchoolInformation)
def create_trial_subscription(sender, instance, created, **kwargs):
    """
    Create a trial subscription when a new school is created.
    """
    if created:
        try:
            # Check if a subscription already exists
            if not hasattr(instance, "subscription"):
                # Get default trial days from settings
                from .models import SuperAdminSettings

                try:
                    settings = SuperAdminSettings.objects.first()
                    trial_days = settings.default_trial_days if settings else 30
                except:
                    trial_days = 30

                # Get the default plan (the cheapest active one)
                try:
                    plan = Plan.objects.filter(is_active=True).order_by("price").first()
                    if not plan:
                        # Create a default plan if none exists
                        plan = Plan.objects.create(
                            name="Basic Plan",
                            description="Default basic plan",
                            price=0.00,
                            billing_cycle="monthly",
                            max_students=100,
                            max_teachers=10,
                            max_storage_gb=1,
                            features={
                                "basic_features": True,
                                "advanced_features": False,
                                "premium_features": False,
                            },
                            is_active=True,
                        )
                except:
                    return  # Can't create subscription without a plan

                # Create the subscription
                Subscription.objects.create(
                    school=instance,
                    plan=plan,
                    status="trial",
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=365),  # Default to 1 year
                    trial_ends_at=timezone.now() + timedelta(days=trial_days),
                    auto_renew=True,
                )
        except Exception as e:
            print(f"Error creating trial subscription: {str(e)}")


@receiver(post_save, sender=Subscription)
def check_subscription_status(sender, instance, **kwargs):
    """
    Update subscription status based on dates.
    """
    # Skip if this is a new subscription (it will have the correct status already)
    if instance.pk is None:
        return

    current_status = instance.status

    # Check if trial has expired
    if (
        current_status == "trial"
        and instance.trial_ends_at
        and instance.trial_ends_at < timezone.now()
    ):
        instance.status = "expired"
        instance.save(update_fields=["status"])

    # Check if subscription has expired
    elif current_status == "active" and instance.end_date < timezone.now():
        instance.status = "expired"
        instance.save(update_fields=["status"])
