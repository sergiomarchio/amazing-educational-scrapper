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


def get_questions(result_page: ResultsPage, max_size=0):
    q_and_a = []
    for result_page in result_page.pages():
        for product_question_page in result_page.question_pages():
            for question_page in product_question_page.pages():
                for question in question_page.questions():
                    q_and_a.append(question)

                    if 0 < max_size <= len(q_and_a):
                        return q_and_a[:max_size]

    return q_and_a


if __name__ == '__main__':
    config = read_conf()

    # Getting data from config file
    request = config['request']
    headers = config['request-headers']
    max_output = config['max-output']

    # Override language and search term with command line parameters, if any
    parser = argparse.ArgumentParser(description="Amazon web Q&A scrapper")
    parser.add_argument("-f", "--file", help="Output file name. Default is search_term_lang_max.json")
    parser.add_argument("-l", "--lang", help="Language for the results, e.g. en, es, ...")
    parser.add_argument("-m", "--max", help="Max number of questions to retrieve. 0 for all the questions")
    parser.add_argument("-s", "--search", help="Term to search for")
    args = parser.parse_args()

    if args.lang:
        headers['Accept-Language'] = args.lang

    if args.search:
        request['keyword'] = args.search

    if args.max:
        max_output = args.max

    max_output = int(max_output)

    # File to save output
    filename = args.file if args.file else \
        f"{request['keyword'].replace(' ', '_')}_{headers['Accept-Language']}_{max_output}.json"

    print("Welcome to Amazon Q&A scrapper")
    print()
    print(f"Searching for '{request['keyword']}' in '{headers['Accept-Language']}' language")
    print(f"Aiming to retrieve {'max' if max_output == 0 else max_output} results")
    print(f"Results are going to be saved to '{filename}'")
    print()

    results_page = ResultsPage(request['url-base'],
                               request['parameters'].format(keyword=request['keyword']),
                               headers)

    results = get_questions(results_page, max_output)
    print()
    print(f"{len(results)} results saved.")

    savefile(results, filename)
