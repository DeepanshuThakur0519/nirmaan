from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import ContractorProfile, QuoteRequest
from .notifications import notify_new_quote, notify_quote_reply, notify_verified


# ---------------------------------------------------------------- quote requests
@receiver(pre_save, sender=QuoteRequest)
def remember_old_quote_status(sender, instance, **kwargs):
    """Just before saving, note what the status was, so we can spot a change."""
    if instance.pk:
        instance._old_status = (
            QuoteRequest.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )
    else:
        instance._old_status = None


@receiver(post_save, sender=QuoteRequest)
def quote_request_saved(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: notify_new_quote(instance))
    elif getattr(instance, "_old_status", None) == "pending" and instance.status in ("accepted", "declined"):
        transaction.on_commit(lambda: notify_quote_reply(instance))


# ---------------------------------------------------------------- verification
@receiver(pre_save, sender=ContractorProfile)
def remember_old_verified(sender, instance, **kwargs):
    if instance.pk:
        instance._was_verified = (
            ContractorProfile.objects.filter(pk=instance.pk).values_list("verified", flat=True).first()
        )
    else:
        instance._was_verified = False


@receiver(post_save, sender=ContractorProfile)
def contractor_profile_saved(sender, instance, created, **kwargs):
    if instance.verified and not getattr(instance, "_was_verified", False):
        transaction.on_commit(lambda: notify_verified(instance))