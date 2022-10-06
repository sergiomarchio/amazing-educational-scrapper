import argparse
import json
import re
import traceback

from config import config
from log import Logger
from page import ResultsPage
from utils import nap


def savefile(lines, file_name: str, file_format="json"):
    if file_format not in ('json', 'txt'):
        Logger.log(f"Format {file_format} not yet available...")

    file_name += f".{file_format}"

    Logger.log()
    Logger.log(f"Saving file '{file_name}'...")

    with open(file_name, 'w', encoding="utf-8") as f:
        if file_format == 'json':
            content = json.dumps(lines)
        else:
            content = "\n".join(lines) + "\n"

        f.write(content)


def save_product_ids(base_name: str, result_page: ResultsPage, max_pag=-1, max_prod=-1):
    """
    Saves product ids from result pages.
    sequential navigation of result pages
    """
    page_counter = 1
    suffix = ""
    prod_ids = []
    try:
        for product, page_count in result_page.items_to_end(max_prod):
            if page_counter > max_pages:
                Logger.log(f"Maximum number of pages reached! ({max_pag})")
                break

            product_id = re.search(r"dp(?:/|(?:%2F))(.*?)(?:/|(?:%2F))", product.parameters).group(1)
            prod_ids.append(product_id)

    except Exception as e:
        Logger.log("Exception while getting Product ids! ", e)
        Logger.log(traceback.format_exc())
        suffix = "_error"
        Logger.log("Saving remains...")

    savefile(prod_ids, f"{base_name}{suffix}", file_format='txt')


def save_q_and_a(base_name: str, result_page: ResultsPage,
                 max_pag=-1, max_prod=-1, max_q_per_prod=-1, max_ans_per_q=-1):
    """
    Saves q & a checkpoints per each results page,
    sequential navigation
    """
    page_counter = 1
    suffix = ""
    q_and_a = []
    try:
        for product, page_count in result_page.items_to_end(max_prod):
            if page_counter > max_pages:
                Logger.log(f"Maximum number of pages reached! ({max_pag})")
                break

            if page_count != page_counter:
                savefile(q_and_a, f"{base_name}_p{page_counter:03}")
                Logger.log(f"Saved page {page_counter:03}...")
                page_counter = page_count
                q_and_a = []

            for question in product.product_questions(max_q_per_prod, max_ans_per_q):
                q_and_a.append(question)

    except Exception as e:
        Logger.log("Exception while getting Q&A! ", e)
        Logger.log(traceback.format_exc())
        suffix = "_error"
        Logger.log("Saving remains...")

    savefile(q_and_a, f"{base_name}_p{page_counter:03}{suffix}")


def get_questions(result_page: ResultsPage, max_prod=-1, max_q_per_prod=-1, max_ans_per_q=-1):
    """
    Gets Q&A and returns a list with the fetched results
    :return:
    q & a list
    """
    q_and_a = []
    for product, page_count in result_page.items_to_end(max_prod):
        nap(3, "fetching next product")
        for question in product.product_questions(max_q_per_prod, max_ans_per_q):
            q_and_a.append(question)

    return q_and_a


if __name__ == '__main__':
    # Getting data from config file
    request = config['request']
    headers = config['request-headers']
    max_pages = config['max-pages']
    max_products = config['max-products']
    max_questions_per_product = config['max-questions-per-product']
    max_answers_per_question = config['max-answers-per-question']

    save_prod_ids = config['save-prod-ids']
    scrap_prod_ids = config['scrap-prod-ids']

    # Override language and search term with command line parameters, if any
    parser = argparse.ArgumentParser(description="Amazon web Q&A scrapper")
    parser.add_argument("-l", "--lang", help="Language for the results, e.g. en, es, ...")
    parser.add_argument("-g", "--max-pages", help="Max number of pages to navigate. -1 for all the pages")
    parser.add_argument("-p", "--max-products", help="Max number of products to retrieve. -1 for all the products")
    parser.add_argument("-q", "--max-questions-per-product",
                        help="Max number of questions per product to retrieve. -1 for all the questions")
    parser.add_argument("-a", "--max-answers-per-question",
                        help="Max number of answers per question to retrieve. -1 for all the answers")
    parser.add_argument("-s", "--search", help="Term to search for")

    parser.add_argument("--save-prod-ids", action='store_true',
                        help="Flag that runs the parser to retrieve only the product ids.")
    parser.set_defaults(save_prod_ids=False)

    parser.add_argument("--scrap-prod-ids", metavar="PROD_IDS_FILENAME",
                        help="Runs the parser targeted to the prod ids obtained from the file.")

    args = parser.parse_args()

    if args.lang:
        headers['Accept-Language'] = args.lang

    if args.search:
        request['keyword'] = args.search

    if args.max_pages:
        max_pages = int(args.max_pages)

    if args.max_products:
        max_products = int(args.max_products)

    if args.max_questions_per_product:
        max_questions_per_product = int(args.max_questions_per_product)

    if args.max_answers_per_question:
        max_answers_per_question = int(args.max_answers_per_question)

    if args.save_prod_ids:
        save_prod_ids = args.save_prod_ids

    if args.scrap_prod_ids:
        scrap_prod_ids = args.scrap_prod_ids

    # File to save output
    filename = None
    if save_prod_ids:
        filename = (f"prod_ids"
                    f"_{headers['Accept-Language']}"
                    f"_{max_products}"
                    f"_{max_questions_per_product}"
                    f"_{max_answers_per_question}"
                    )
    elif not scrap_prod_ids:
        filename = (f"{request['keyword'].replace(' ', '_')}"
                    f"_{headers['Accept-Language']}"
                    f"_{max_products}"
                    f"_{max_questions_per_product}"
                    f"_{max_answers_per_question}"
                    )

    Logger.log("Welcome to Amazon Q&A scrapper")
    Logger.log()
    Logger.log(f"Searching for '{request['keyword']}' in '{headers['Accept-Language']}' language")
    Logger.log(f"Aiming to retrieve"
               f" {'max' if max_answers_per_question == -1 else max_answers_per_question} answers per question"
               f", {'max' if max_questions_per_product == -1 else max_questions_per_product} questions per product"
               f", {'max' if max_products == -1 else max_products} products"
               f", {'max' if max_pages == -1 else max_pages} pages.")

    Logger.log()

    results_page = ResultsPage(request['url-base'],
                               request['parameters'].format(keyword=request['keyword']),
                               headers)

    if save_prod_ids:
        save_product_ids(filename, results_page,
                         max_pag=max_pages,
                         max_prod=max_products)
    elif scrap_prod_ids:
        pass
    else:
        save_q_and_a(filename, results_page,
                     max_pag=max_pages,
                     max_prod=max_products,
                     max_q_per_prod=max_questions_per_product,
                     max_ans_per_q=max_answers_per_question)
