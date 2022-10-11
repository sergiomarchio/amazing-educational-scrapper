from abc import abstractmethod
from dateparser.search import search_dates
from bs4 import BeautifulSoup
from requests import HTTPError
from urllib.parse import urljoin

import re
import requests

from config import config
from log import save_debug, Logger
from utils import nap


class Page:
    """
    Base class common for every page
    """

    def __init__(self, base_url, parameters='', headers=None):
        if headers is None:
            headers = {}
        self.base_url = base_url
        self.parameters = parameters
        self.headers = headers
        self._url = None
        self._soup = None

    @property
    def url(self):
        if self._url is None:
            self._url = urljoin(self.base_url, self.parameters)
        return self._url

    @property
    def soup(self):
        if self._soup is None:
            self._soup = self.get_soup()
        return self._soup

    def get_soup(self):
        attempt_number = config['request-attempts']

        for i in range(1, attempt_number + 1):
            Logger.log(f"{i}{'st' if i == 1 else 'nd' if i == 2 else 'rd' if i == 3 else 'th'}"
                       f" attempt of request to {self.url}")

            r = requests.get(self.url, headers=self.headers)

            if 200 <= r.status_code < 400:
                return BeautifulSoup(r.content, 'html.parser')

            Logger.log(f"Request status code: {r.status_code}")

            nap(config['nap-request'], "making next request attempt")

        raise HTTPError(f"Request still failing after {attempt_number} attempts")

    def content_error(self):
        """
        When the page content required is not present, performs the logging if log setting is on
        """
        Logger.log()
        Logger.log(f"Failed request for {self.url}")
        save_debug(self.soup.prettify())
        raise ValueError("Page was not loaded correctly")


class PaginatedPage(Page):
    """
    Class to model paginated pages:
    i.e. pages that have a "next" button with more results
    """
    next_button_locator = None

    def pages(self):
        """
        :return:
        the next results page until there are no more pages
        """
        if not self.next_button_locator:
            raise AttributeError("PaginatedPage objects must have a next_button_locator attribute!")

        # the first page returned is the same page
        yield self

        next_button = self.soup.select_one(self.next_button_locator)
        while next_button is not None:
            nap(1, "getting next page")
            next_page = type(self)(self.base_url, parameters=next_button['href'], headers=self.headers)
            yield next_page

            next_button = next_page.soup.select_one(self.next_button_locator)

    @abstractmethod
    def items(self, max_items=-1, **kwargs):
        pass

    def items_to_end(self, max_items=-1, **kwargs):
        """
        this method provides the items, navigating the pagination for the current page to the end
        :param max_items:
        maximum number of items to be collected.
        if -1, gets all items available
        :params kwargs:
        kwargs required by the items() method
        :return:
        items one by one
        """
        if max_items == 0:
            Logger.log("no items required...")
            return

        item_count = 0
        page_count = 0
        for page in self.pages():
            page_count += 1

            if item_count == max_items:
                Logger.log(f"Already collected max number of items: {max_items}")
                break

            for item in page.items(max_items - item_count, **kwargs):
                yield item, page_count
                item_count += 1


class ResultsPage(PaginatedPage):
    """
    Class to model results page
    """
    next_button_locator = ".s-pagination-next:not(.s-pagination-disabled)"
    product_locator = "[data-component-type='s-search-result']"
    product_link_locator = "h2 a"

    def items(self, max_items=-1, **kwargs):
        products = self.soup.select(self.product_locator)
        if not products:
            self.content_error()
            return None

        product_count = 0
        for product in products:
            if product_count == max_items:
                Logger.log(f"Already collected max number of products: {max_items}")
                break

            product_link = product.select_one(self.product_link_locator)

            if product_link:
                yield ProductPage(self.base_url, product_link['href'], headers=self.headers)
                product_count += 1
            else:
                self.content_error()


class ProductPage(Page):
    """
    Class to model product page
    """
    asin_locator = "#ASIN"
    name_locator = "#productTitle"
    ratings_count_locator = "#acrCustomerReviewText"

    @staticmethod
    def from_product_id(base_url: str, product_id: str, headers):
        """
        :return:
        a new ProductPage object corresponding to the provided product id
        """
        params = f"-/{headers['Accept-Language']}/dp/{product_id}/"
        return ProductPage(base_url=base_url, parameters=params, headers=headers)

    def product_questions(self, max_questions=-1, max_answers_per_question=-1):
        """
        :param max_questions:
        maximum number of questions to be collected per product.
        if -1, gets all questions available
        :param max_answers_per_question:
        maximum number of answers to be collected per question.
        if -1, gets all answers available
        :return:
        the first question page for this product
        """

        asin_soup = self.soup.select_one(self.asin_locator)
        name_soup = self.soup.select_one(self.name_locator)
        ratings_count_soup = self.soup.select_one(self.ratings_count_locator)

        if not asin_soup or not name_soup:
            self.content_error()
            return None

        asin = asin_soup['value']
        name = name_soup.text.strip()
        ratings_count_text = ratings_count_soup.text if ratings_count_soup else ""

        match = re.search(r"\d+", ratings_count_text)
        ratings_count = int(match.group()) if match else 0

        question_href = (f"-/{self.headers['Accept-Language']}"
                         f"/ask/questions/asin/{asin}/ref=ask_dp_dpmw_ql_hza?isAnswered=true")

        questions_page = QuestionsPage(self.base_url, question_href, headers=self.headers)

        for question, page_count in questions_page.items_to_end(max_questions,
                                                                max_answers_per_question=max_answers_per_question):

            question['product_id'] = asin
            question['product_name'] = name
            question['product_ratings_count'] = ratings_count

            yield question


class QuestionsPage(PaginatedPage):
    """
    Class to model questions page
    """
    next_button_locator = ".a-last:not(.a-disabled) a"

    card_locator = ".askTeaserQuestions > div"
    votes_locator = ".vote .count"
    question_locator = "[id^='question']"
    question_link_locator = "a"

    def items(self, max_items=-1, max_answers_per_question=-1):
        """
        :param max_items:
        maximum number of items to retrieve
        if -1, gets all items available
        :param max_answers_per_question:
        maximum number of answers to be collected per question.
        if -1, gets all answers available
        :return:
        questions one by one for the current page
        """
        question_count = 0
        for card in self.soup.select(self.card_locator):
            if question_count == max_items:
                Logger.log(f"Already collected max number of questions: {max_items}")
                break

            question_soup = card.select_one(self.question_locator)
            question_link_soup = question_soup.select_one(self.question_link_locator)

            if not question_soup or not question_link_soup:
                self.content_error()
                continue

            question_count += 1

            votes_soup = card.select_one(self.votes_locator)
            question_text = question_link_soup.text.strip()
            try:
                votes_value = int(votes_soup.text)
            except (AttributeError, ValueError):
                votes_value = 0

            answers_page = AnswersPage(self.base_url, question_link_soup['href'], self.headers)
            answers = [a for a, page_count in answers_page.items_to_end(max_answers_per_question)]

            question = {
                "id": question_soup['id'],
                "question": question_text,
                "votes": votes_value,
                "date": answers_page.question_date(),
                "answers": answers
            }

            yield question


class AnswersPage(PaginatedPage):
    """
    Class to model answers page:
    the page that holds answers for one question
    """
    next_button_locator = ".a-last:not(.a-disabled) a"

    question_date_locator = ".a-size-large.askWrapText + p"
    card_locator = "[id^='answer']"
    text_locator = "span"  # it is the first span
    date_locator = ".a-spacing-small > span"
    badge_locator = ".askNewAuthorBadge"
    votes_locator = ".askVoteAnswerTextWithCount"

    def date_string_from_soup(self, soup, date_format="%Y/%m/%d"):
        date = search_dates(soup.text, languages=[self.headers['Accept-Language']])[0][1] if soup else None
        return date.strftime(date_format) if date else ""

    def question_date(self):
        """
        :return:
        the date of the question
        """
        question_date_soup = self.soup.select_one(self.question_date_locator)

        return self.date_string_from_soup(question_date_soup)

    def items(self, max_items=-1, **kwargs):
        answer_count = 0
        for card in self.soup.select(self.card_locator):
            if answer_count == max_items:
                Logger.log(f"Already collected max number of answers: {max_items}")
                break

            answer_soup = card.select_one(self.text_locator)
            if not answer_soup:
                self.content_error()
                continue

            answer_count += 1

            date_soup = card.select_one(self.date_locator)
            badge_soup = card.select_one(self.badge_locator)
            votes_soup = card.select_one(self.votes_locator)

            answer_text = answer_soup.text.strip()
            date_text = self.date_string_from_soup(date_soup)

            badge_text = badge_soup.text.strip() if badge_soup else ""
            is_manufacturer = "manufacturer" in badge_text.lower()
            is_seller = "seller" in badge_text.lower()

            upvotes = 0
            downvotes = 0
            if votes_soup:
                match = re.search(r".*?(?P<upvotes>\d+).*? .*?(?P<allvotes>\d+).*?", votes_soup.text)
                if match:
                    votes = match.groupdict()
                    upvotes = int(votes['upvotes'])
                    downvotes = int(votes['allvotes']) - upvotes

            answer = {
                "id": card['id'],
                "url": self.url,
                "answer": answer_text,
                "badge_text": badge_text,
                "is_manufacturer": is_manufacturer,
                "is_seller": is_seller,
                "date": date_text,
                "upvotes": upvotes,
                "downvotes": downvotes
            }

            yield answer

