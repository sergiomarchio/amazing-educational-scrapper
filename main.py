import argparse
import json
import yaml

from page import ResultsPage


def read_conf():
    with open('config.yml', 'r') as f:
        return yaml.safe_load(f)


def savefile(lines, file_name: str):
    print()
    print(f"Saving file '{file_name}'...")

    with open(file_name, 'w') as f:
        f.write(json.dumps(lines))


def get_questions(result_page: ResultsPage, max_q=-1, max_ans_per_q=-1):
    q_and_a = []
    for result_page in result_page.pages():
        for product_question_page in result_page.question_pages():
            for question in product_question_page.questions_to_end(max_q, max_ans_per_q):
                q_and_a.append(question)

            return q_and_a

    return q_and_a


if __name__ == '__main__':
    config = read_conf()

    # Getting data from config file
    request = config['request']
    headers = config['request-headers']
    max_questions = config['max-questions']
    max_answers_per_question = config['max-answers-per-question']

    # Override language and search term with command line parameters, if any
    parser = argparse.ArgumentParser(description="Amazon web Q&A scrapper")
    parser.add_argument("-f", "--file", help="Output file name. Default is search_term_lang_max.json")
    parser.add_argument("-l", "--lang", help="Language for the results, e.g. en, es, ...")
    parser.add_argument("-q", "--max-questions", help="Max number of questions to retrieve. -1 for all the questions")
    parser.add_argument("-a", "--max-answers-per-question",
                        help="Max number of answers per question to retrieve. -1 for all the answers")
    parser.add_argument("-s", "--search", help="Term to search for")
    args = parser.parse_args()

    if args.lang:
        headers['Accept-Language'] = args.lang

    if args.search:
        request['keyword'] = args.search

    if args.max_questions:
        max_questions = int(args.max_questions)

    if args.max_answers_per_question:
        max_answers_per_question = int(args.max_answers_per_question)

    # File to save output
    filename = args.file if args.file else \
        f"{request['keyword'].replace(' ', '_')}_{headers['Accept-Language']}_{max_questions}.json"

    print("Welcome to Amazon Q&A scrapper")
    print()
    print(f"Searching for '{request['keyword']}' in '{headers['Accept-Language']}' language")
    print(f"Aiming to retrieve {'max' if max_questions == 0 else max_questions} results")
    print(f"Results are going to be saved to '{filename}'")
    print()

    results_page = ResultsPage(request['url-base'],
                               request['parameters'].format(keyword=request['keyword']),
                               headers)

    results = get_questions(results_page, max_questions, max_answers_per_question)
    print()
    print(f"{len(results)} results saved.")

    savefile(results, filename)
