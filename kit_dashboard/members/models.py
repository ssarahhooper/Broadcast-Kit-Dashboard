from django.db import models

# Create your models here.


class Kit(models.Model):
    name = models.CharField(max_length=120)
    issues = models.TextField(blank=True, null=True)
    needs_restock = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PostMortem(models.Model):
    kit = models.ForeignKey(Kit, on_delete=models.CASCADE)
    name = models.CharField(max_length=120, blank=True, null=True)
    event_name = models.CharField(max_length=120)
    event_date = models.DateField()
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    slack_thread_ts = models.CharField(max_length=50,null=True, blank=True)
    slack_first_reply_ts = models.CharField(max_length=50,null=True, blank=True)

    def __str__(self):
        return self.event_name
