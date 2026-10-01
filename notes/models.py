from django.db import models

class Category(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Note(models.Model):
    title = models.CharField(max_length=200)
    text = models.TextField()
    reminder = models.DateTimeField(null=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='notes'
    )

    class Meta:
        ordering = ['-pk']

    def __str__(self):
        return self.title
