import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
from celery import shared_task
from django.utils import timezone
from .models import CrawlRequest, PageData
from django.conf import settings
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

nltk.download('stopwords')
nltk.download('wordnet')


def _crawl_and_extract_metadata(url):
    try:
        headers = {
            'User-Agent': settings.CRAWLER_USER_AGENT
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.title.string if soup.title else 'No Title Found'

        description = ''
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description and meta_description.get('content'):
            description = meta_description['content']
        else:
            meta_description = soup.find('meta', attrs={'property': 'og:description'})
            if meta_description and meta_description.get('content'):
                description = meta_description['content']

        body_text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'span'])
        body_text = ' '.join([element.get_text(separator=' ', strip=True) for element in body_text_elements])
        body_text = re.sub(r'\s+', ' ', body_text).strip()

        return {
            'url': url,
            'title': title,
            'description': description,
            'body_text': body_text
        }

    except requests.exceptions.RequestException as e:
        print(f"Error crawling {url}: {e}")
        return None


def _classify_page(text, num_topics=5):
    if not text:
        return []

    text = text.lower()
    clean_regex = re.compile(r'[^a-z\s]')
    text = clean_regex.sub('', text)

    words = text.split()

    stop_words = set(stopwords.words('english'))

    lemmatiser = WordNetLemmatizer()

    filtered_words = []
    for word in words:
        if len(word) > 2 and word not in stop_words:
            lemma = lemmatiser.lemmatize(word)
            filtered_words.append(lemma)

    word_counts = Counter(filtered_words)
    relevant_topics = [word for word, count in word_counts.most_common(num_topics)]
    return relevant_topics


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def perform_crawl_task(self, crawl_request_id):
    """
    Celery task to perform the web crawling and store data.
    """
    try:
        crawl_request = CrawlRequest.objects.get(id=crawl_request_id)
        crawl_request.status = 'IN_PROGRESS'
        crawl_request.started_at = timezone.now()
        crawl_request.save()

        print(f"Starting crawl for: {crawl_request.url}")

        page_data_raw = _crawl_and_extract_metadata(crawl_request.url)

        if page_data_raw:
            topics = _classify_page(page_data_raw['body_text'])

            PageData.objects.create(
                crawl_request=crawl_request,
                title=page_data_raw['title'],
                description=page_data_raw['description'],
                body_text=page_data_raw['body_text'],
                relevant_topics=", ".join(topics)
            )
            crawl_request.status = 'COMPLETED'
            print(f"Crawl COMPLETED for: {crawl_request.url}")
        else:
            crawl_request.status = 'FAILED'
            print(f"Crawl FAILED for: {crawl_request.url}")

    except CrawlRequest.DoesNotExist:
        print(f"CrawlRequest with ID {crawl_request_id} not found.")
        self.retry(exc=CrawlRequest.DoesNotExist("CrawlRequest not found, retrying."),
                   countdown=10)
    except requests.exceptions.RequestException as e:
        print(f"Request error during crawl for {crawl_request.url}: {e}")
        crawl_request.status = 'FAILED'
        raise self.retry(exc=e, countdown=60)
    except Exception as e:
        print(f"An unexpected error occurred during crawl for {crawl_request.url}: {e}")
        crawl_request.status = 'FAILED'
    finally:
        crawl_request.completed_at = timezone.now()
        crawl_request.save()
