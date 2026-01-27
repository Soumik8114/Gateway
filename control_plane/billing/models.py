from django.db import models

class Plan(models.Model):
    name = models.CharField(max_length=50)
    requests_per_minute = models.IntegerField()
    requests_per_month = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
