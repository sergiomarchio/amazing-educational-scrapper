from dateparser.search import search_dates
from dateparser.date import DateDataParser
from bs4 import BeautifulSoup
from urllib.parse import urljoin

import re
import requests


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
        print(f"making request to {self.url}")
        r = requests.get(self.url, headers=self.headers)
        return BeautifulSoup(r.content, 'html.parser')


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
            next_page = type(self)(self.base_url, parameters=next_button['href'], headers=self.headers)
            # next_page.soup    # load soup once
            yield next_page

            next_button = next_page.soup.select_one(self.next_button_locator)


class ResultsPage(PaginatedPage):
    """
    Class to model results page
    """
    next_button_locator = ".s-pagination-next:not(.s-pagination-disabled)"
    product_locator = "[data-component-type='s-search-result']"
    product_link_locator = "[data-component-type='s-search-result'] h2 a"

    def question_pages(self):
        """
        :return:
        A list with the first question page for each product in this result page
        """
        products = self.soup.select(self.product_locator)
        if products is None:
            return None

        asin_values = [p.attrs['data-asin'] for p in products]
        parameters = [
            f"-/{self.headers['Accept-Language']}/ask/questions/asin/{asin}/ref=ask_dp_dpmw_ql_hza?isAnswered=true"
            for asin in asin_values]

        return [QuestionsPage(self.base_url, param, self.headers) for param in parameters]


class QuestionsPage(PaginatedPage):
    """
    Class to model questions page
    """
    next_button_locator = ".a-last:not(.a-disabled) a"

    card_locator = ".askTeaserQuestions > div"
    votes_locator = ".vote .count"
    question_link_locator = "[id^='question'] a"

    def questions(self, max_questions=-1, max_answers=-1):
        """
        :param max_questions:
        maximum number of questions to be collected in this page.
        if -1, gets all questions available
        :param max_answers:
        maximum number of answers to be collected by this question.
        if -1, gets all answers available
        :return:
        all the questions for the current page, one by one, containing all the answers available
        """
        question_count = 0
        answer_count = 0
        for card in self.soup.select(self.card_locator):
            if question_count == max_questions or answer_count == max_answers:
                break

            question_soup = card.select_one(self.question_link_locator)
            if not question_soup:
                continue
            question_count += 1

            votes_soup = card.select_one(self.votes_locator)

            question_text = question_soup.text.strip()
            try:
                votes_value = int(votes_soup.text)
            except (AttributeError, ValueError):
                votes_value = 0

            answers = []
            answers_page = AnswersPage(self.base_url, question_soup['href'], self.headers)
            for page in answers_page.pages():
                for answer in page.answers(max_answers - answer_count):
                    answers.append(answer)
                    answer_count += len(answers)

                if answer_count == max_answers:
                    break

            question = {
                "question": question_text,
                "votes": votes_value,
                # "product_name": pr,
                # "product_ratings_count": pr,
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

    def answers(self, max_answers=-1):
        """
        :param max_answers:
        maximum number of answers to be returned from this page.
        if -1, gets all answers available
        :return:
        all answers for the page, one by one
        """
        answer_count = 0
        for card in self.soup.select(self.card_locator):
            if answer_count == max_answers:
                break

            answer_soup = card.select_one(self.text_locator)
            if not answer_soup:
                continue
            answer_count += 1

            date_soup = card.select_one(self.date_locator)
            badge_soup = card.select_one(self.badge_locator)
            votes_soup = card.select_one(self.votes_locator)

            answer_text = answer_soup.text.strip()
            date_text = self.date_string_from_soup(date_soup)

            is_manufacturer = False
            is_seller = False
            if badge_soup:
                is_manufacturer = "manufacturer" in badge_soup.text.lower()
                is_seller = "seller" in badge_soup.text.lower()

            upvotes = 0
            downvotes = 0
            if votes_soup:
                match = re.search(r".*?(?P<upvotes>\d+).*? .*?(?P<allvotes>\d+).*?", votes_soup.text)
                if match:
                    votes = match.groupdict()
                    upvotes = int(votes['upvotes'])
                    downvotes = int(votes['allvotes']) - upvotes

            answer = {
                "url": self.url,
                "answer": answer_text,
                "is_manufacturer": is_manufacturer,
                "is_seller": is_seller,
                "date": date_text,
                "upvotes": upvotes,
                "downvotes": downvotes
            }

            yield answer
