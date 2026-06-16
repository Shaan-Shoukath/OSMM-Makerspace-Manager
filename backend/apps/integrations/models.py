from django.db import models

from apps.makerspaces.secrets import decrypt_value, encrypt_value


class PlatformEmailSettings(models.Model):
    smtp_host = models.CharField(max_length=200, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=200, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)
    from_email = models.EmailField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_smtp_password(self, raw):
        self.smtp_password = encrypt_value(raw) if raw else ""

    def get_smtp_password(self):
        return decrypt_value(self.smtp_password) if self.smtp_password else ""

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Platform email settings"
