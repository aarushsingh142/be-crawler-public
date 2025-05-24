from django.db import models


class CrawlRequest(models.Model):
    url = models.URLField(max_length=500, unique=True)
    status = models.CharField(
        max_length=20,
        default='PENDING',
        choices=[
            ('PENDING', 'Pending'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ]
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    task_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Crawl for {self.url} ({self.status})"


class PageData(models.Model):
    crawl_request = models.ForeignKey(CrawlRequest, on_delete=models.CASCADE, related_name='page_data')
    title = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    body_text = models.TextField(blank=True, null=True)
    crawled_at = models.DateTimeField(auto_now_add=True)
    relevant_topics = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Data for {self.crawl_request.url[:50]}..."
