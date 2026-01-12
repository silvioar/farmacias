from django.db import models
from django.contrib.auth.models import User

class VisitStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    apellido = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    localidad = models.CharField(max_length=100)
    visitado = models.BooleanField(default=False)

    class Meta:
        # app_label = 'routes' # Not strictly needed if inside the app, but good practice if mixed
        unique_together = ('user', 'apellido', 'direccion', 'localidad')

    def __str__(self):
        return f"{self.user.username} - {self.apellido} - {self.visitado}"
