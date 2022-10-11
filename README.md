# Amazon Question & Answer Educational Scrapper

> Disclaimer: This project is intended for educational purposes only.


## Brief description

This project implements a web scrapper to get Questions and Answers from amazon website.
The output is a JSON file with a list of questions. Each questions holds information from its product, and a list of answers.
The JSON follows the following structure:

```json
[
  {
    "id": "question-1-id",
    "question": "Will this work on holidays?",
    "votes": 1,
    "date": "2018/02/02",
    "answers": [
      {
        "id": "answer-1-id",
        "url": "https://answer-1-url",
        "answer": "No, I don't think it will work.",
        "badge_text": "",
        "is_manufacturer": false,
        "is_seller": false,
        "date": "2018/11/18",
        "upvotes": 1,
        "downvotes": 3
      },
      {
        "id": "answer-2-id",
        "url": "https://answer-2-url",
        "answer": "It worked for me!",
        "badge_text": "",
        "is_manufacturer": false,
        "is_seller": false,
        "date": "2030/10/01",
        "upvotes": 11,
        "downvotes": 0
      }, 
      ...
    ],
    "product_id": "product-id",
    "product_name": "time machine",
    "product_ratings_count": 3
  },
  ...
]
```


## How to use

### Setup

From the project's root directory, in the console:

 - Create virtual environment

`python -m venv scrapper`

 - Activate it

   - Linux / MacOS:
   - `source scrapper/bin/activate`

   - Windows
   - `scrapper\Scripts\activate.bat`


 - install required packages

`pip install -r requirements.txt`


### Configuration

Configurations can be provided in the [config.yml](config.yml) file, and some can be provided by command line parameters.
To get the available command line parameters, you can execute
```
python main.py -h
```

### Scrapping by sequential navigation

if the parameter `scrap-prod-ids:` from [config.yml](config.yml) is left empty, the scrapper will run in sequential mode, navigating each of the results page, entering each product page to fetch the questions and answers, saving the output in different files, one for each result page.


### Scrapping by product id

First, set the parameter `save-prod-ids: True` in [config.yml](config.yml) or run with the command line parameter `--save-prod-ids`.
It will navigate the results pages fetching the product ids and saving them in a file with the naming `prod_ids_<language_code>_<max_products>.txt`

Then, setting the parameter `scrap-prod-ids: <product_ids_filename>` in [config.yml](config.yml) or running with the command line parameter `--scrap-prod-ids <product_ids_filename>`.
It will go to each product page form the list, and retrieve the questions and answers from that product, saving it to a json file with the name `<product_id>.json`.
The saved product ids will be registered in a file named `saved_ids.txt`, in order to be able to resume the scrapping  in another session if needed. On subsequent runs, the ids in this file will be ignored.


Happy learning! :)
