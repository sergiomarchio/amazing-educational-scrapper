from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


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


class ResultsPage(Page):
    """
    Class to model results page
    """
    next_button_locator = ".s-pagination-next:not(.s-pagination-disabled)"
    product_locator = "[data-component-type='s-search-result']"
    product_link_locator = "[data-component-type='s-search-result'] h2 a"

    def pages(self):
        """
        :return:
        the next results page until there are no more pages
        """
        next_button = self.soup.select_one(self.next_button_locator)
        while next_button is not None:
            parameters = urljoin(self.base_url, next_button['href'])
            next_page = ResultsPage(self.base_url, parameters, self.headers)
            next_page.soup    # load soup once
            yield next_page

            next_button = next_page.soup.select_one(self.next_button_locator)

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


class QuestionsPage(Page):
    """
    Class to model questions page
    """
    next_button_locator = ".a-last:not(.a-disabled) a"

    qa_block_locator = ".askTeaserQuestions > .a-fixed-left-grid > .a-fixed-left-grid-inner"
    votes_locator = "[data-count]"
    votes_value = "data-count"
    question_locator = "[data-ask-no-op='{\"metricName\":\"top-question-text-click\"}']"
    answer_locator = ".a-col-right .a-col-right > span:not(.askInlineAnswers)"
    more_answers_locator = "[id^='askSeeAllAnswersLink']"

    def pages(self):
        """
        :return:
        The next question page until there are no more pages
        """
        next_button = self.soup.select_one(self.next_button_locator)
        while next_button is not None:
            parameters = urljoin(self.base_url, next_button['href'])
            next_question = QuestionsPage(self.base_url, parameters, self.headers)
            next_question.soup    # load soup once
            yield next_question

            next_button = next_question.soup.select_one(self.next_button_locator)

    def get_questions(self):
        """
        :return:
        A list of all the questions and answers for the current question page
        """
        qa_blocks = self.soup.select(self.qa_block_locator)
        if qa_blocks is None:
            return None

        question_list = []
        for qa_block in qa_blocks:
            question = qa_block.select_one(self.question_locator)
            answers = qa_block.select(self.answer_locator)
            votes = qa_block.select_one(self.votes_locator)

            try:
                votes_value = int(votes[self.votes_value])
            except ValueError:
                votes_value = 0

            if question is None or answers is None or len(answers) == 0:
                continue

            # The last because if answer is shortened, the last item is the complete answer
            answer = qa_block.select(self.answer_locator)[-1]

            question_list.append({'question': question.text.strip(),
                                  'votes': votes_value,
                                  'answer': answer.text.strip()})

        print(f"{len(question_list)} results retrieved")

        return question_list

