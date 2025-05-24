from django.shortcuts import render, redirect, get_object_or_404
from .models import CrawlRequest, PageData
from .tasks import perform_crawl_task
from django.contrib import messages


def crawl_dashboard(request):
    crawl_requests = CrawlRequest.objects.all().order_by('-started_at')
    return render(request, 'crawler_app/dashboard.html', {'crawl_requests': crawl_requests})


def request_crawl(request):
    if request.method == 'POST':
        url = request.POST.get('url')
        if url:
            try:
                crawl_request, created = CrawlRequest.objects.get_or_create(url=url)
                if not created and crawl_request.status in ['PENDING', 'IN_PROGRESS']:
                    messages.info(request, f"Crawl for {url} is already {crawl_request.status.lower()}.")
                else:
                    crawl_request.status = 'PENDING'
                    crawl_request.started_at = None
                    crawl_request.completed_at = None
                    crawl_request.save()

                    task = perform_crawl_task.delay(crawl_request.id)
                    crawl_request.task_id = task.id
                    crawl_request.save()
                    messages.success(request, f"Crawl request for {url} submitted successfully! Task ID: {task.id}")
            except Exception as e:
                messages.error(request, f"Error submitting crawl request: {e}")
        else:
            messages.error(request, "Please provide a URL to crawl.")
    return redirect('crawl_dashboard')


def view_crawled_data(request, request_id):
    crawl_request = get_object_or_404(CrawlRequest, id=request_id)
    page_data = PageData.objects.filter(
        crawl_request=crawl_request).first()
    return render(request, 'crawler_app/view_data.html', {'crawl_request': crawl_request, 'page_data': page_data})
