from django.db import models

class AppVersion(models.Model):
    supportEnum = (
        ('ipa', 'ios'),
        ('apk', 'Android'),
        ('app','Mac'),
        ('exe','Windows')
    )
     
    version_number = models.CharField(max_length=10)
    support = models.CharField( max_length=8, choices=supportEnum, unique=True )

    def __str__(self):
        return f"Version {self.get_support_display()} {self.version_number} "