#!/usr/bin/env python
# coding: utf-8
import csv
import re
from collections import Counter
from os import listdir
from os.path import isfile, join

import docx
import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer


def concat(policy, note):
    text = 'NA'
    if type(policy) == str:
        text = policy
    if type(note) == str:
        if text != 'NA':
            text += '. ' + note
        else:
            text = note
    return text


def sentence_tokenize(paragraph):
    l_s = nltk.sent_tokenize(paragraph.lower())

    d_s = {}
    for sent in l_s:

        if 'rate' in sent:

            count = sent.count('rate')
            if sent not in d_s:
                d_s[sent] = count
            else:
                d_s[sent] += count

    sent_count = 0
    sent_string = ''

    for key in d_s:
        sent_count += d_s[key]
        sent_string += key

    return d_s, sent_string, sent_count


def tokenize(fragment):
    fragments = nltk.sent_tokenize(fragment)
    tokens = fragments
    # Removes punctuation, paranthesis etc.
    # tokens = re.sub(r'[^\w\s]', ' ', tokens)
    # Makes lower case
    # tokens = tokens.lower()
    # Makes each word into a token in the sentece
    tokens = [word_tokenize(fragment) for fragment in fragments]
    # Removes english stopwords
    # tokens = list(set(tokens) - stop)
    # Lemmatizes each word
    return tokens


# Returns the results ordered
def lms(tokens, idf_dict, sent_dict, sent_cols):
    sent_dict = lm_sent(tokens, idf_dict, sent_dict)
    sent_list = []
    for key in sent_cols:
        sent_list.append(sent_dict[key])
    return sent_list


# Creates a table with the idf scores with each word
def idf(fragments):
    vectorizer = TfidfVectorizer(min_df=1)
    X = vectorizer.fit_transform(fragments)
    idf = vectorizer.idf_
    return dict(zip(vectorizer.get_feature_names(), idf))


def lm_sent(tokens, idf_dict, sent_dict):
    # Rules

    tokens = [val for sublist in tokens for val in sublist]

    tokens_len = len(tokens)
    remove_indices = []
    if 'effective' in set(tokens):
        for index in range(tokens_len - 1):
            if (tokens[index] == 'effective') & (tokens[index + 1] in ('income', 'tax', 'rate')):
                remove_indices.append(index)
                print('rule 1 applied')
    if 'efficiency' in set(tokens):
        for index in range(tokens_len - 1):
            if (tokens[index] == 'efficiency') & (tokens[index + 1] in ('ratio')):
                remove_indices.append(index)
                print('rule 2 applied')

    # Removes the words by indexes
    if not remove_indices:
        # print tokens
        for index in remove_indices:
            tokens.pop(index)
        # print tokens

    return_dict = {}
    for key in sent_dict.keys():
        return_dict[key] = 0.0

    # Makes the tokens into a dict of counts
    counts = Counter(tokens)

    if len(counts) != 0:  # List of tokens might be empty
        # The token might be in several sets
        tokensCount = 0
        for token in counts:
            token = token.lower()
            for key in sent_dict.keys():
                # The token might be in many sets
                if token in sent_dict[key]:
                    try:
                        # Fetches the already calculated idfscore
                        idf_score = idf_dict[token]
                        # Calculates the tfidfScore
                        tfidf = idf_score * counts[token] / len(counts)
                        return_dict[key] += tfidf
                    except Exception as e:
                        print(e)
                        print(token)
    return return_dict


def analyse_from_excel():
    data = pd.read_excel('input-file.xlsx', sheet_name='Sheet3')
    data.head(3)
    data.info()
    data['Text'] = data.apply(lambda row: concat(row['All notes'], row['empty']), axis=1)
    data.Text.describe()
    data.info()
    data.Text.head()
    nltk.sent_tokenize(data.Text.head()[0])
    data[['rate_d', 'rate_sentences', 'rate_count']] = data.Text.apply(lambda paragraph: pd.Series(sentence_tokenize(paragraph)))
    data['rate_count'].describe()

    stop = set(stopwords.words('english'))
    wordnet_lemmatizer = WordNetLemmatizer()

    data['Tokens'] = data.Text.apply(lambda text: tokenize(str(text)))

    data.Tokens.head()

    data.Text.head()

    lm_panda = pd.read_csv('LoughranMcDonald_MasterDictionary_2016.csv')
    sent_cols = ['Negative', 'Positive', 'Uncertainty', 'Litigious', 'Constraining', 'Superfluous', 'Interesting', 'Modal']
    sent_dict = {}

    for col in sent_cols:
        sent_dict[col] = set([x.lower() for x in lm_panda[lm_panda[col] != 0]['Word'].tolist()])
    all_lists = data.Tokens.tolist()
    tokens_list = [val for sublist in all_lists for val in sublist]
    tokens_list = [val for sublist in tokens_list for val in sublist]

    # Creats the table with the idf scores
    idf_dict = idf(tokens_list)

    data.Tokens.head().apply(lambda note: lms(note, idf_dict, sent_dict, sent_cols))
    sent_col = [col for col in sent_cols]
    data[sent_col] = data.Tokens.apply(lambda note_tokens: pd.Series(lms(note_tokens, idf_dict, sent_dict, sent_cols)))
    data[sent_col].head()


def read_from_word(path):
    results = []
    for file_name in listdir(path):
        file_path = join(path, file_name)
        if isfile(file_path) and file_name.endswith(('.doc', '.docx')):
            results.append(extract_text_from_word(file_path, file_name))
    with open('input.csv', 'w', newline='\n', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=';')
        for result in results:
            csv_writer.writerow(result)


def extract_text_from_word(file_path, file_name):
    title, year = file_name.split('.')[0].split('_')
    document = docx.Document(file_path)
    doc_text = ''.join([paragraph.text for paragraph in document.paragraphs])
    doc_text = doc_text.replace('\n', ' ')
    doc_text = doc_text.replace('"', ' ')
    doc_text = doc_text.replace(';', ' ')
    doc_text = re.sub(r' {2,}', ' ', doc_text)
    return [title, year, doc_text]


# def read_from_input_csv(file_name):
#     results = []
#     with open(file_name, 'r', encoding='utf-8') as csv_file:
#         csv_reader = csv.reader(csv_file, delimiter=';')
#         for title, year, text in csv_reader:
#             results.append([title, year, text])
#     return results


def analyse_from_word(source_folder_path, csv_file_path):
    read_from_word(source_folder_path)
    data = pd.read_csv(csv_file_path, delimiter=';')
    data.head(3)
    data.info()
    data['Text'] = data.apply(lambda row: row[2], axis=1)
    data.Text.describe()
    data.info()
    data.Text.head()
    nltk.sent_tokenize(data.Text.head()[0])
    data[['rate_d', 'rate_sentences', 'rate_count']] = data.Text.apply(lambda paragraph: pd.Series(sentence_tokenize(paragraph)))
    data['rate_count'].describe()

    stop = set(stopwords.words('english'))
    wordnet_lemmatizer = WordNetLemmatizer()

    data['Tokens'] = data.Text.apply(lambda text: tokenize(str(text)))

    data.Tokens.head()

    data.Text.head()

    lm_panda = pd.read_csv('LoughranMcDonald_MasterDictionary_2016.csv')
    sent_cols = ['Negative', 'Positive', 'Uncertainty', 'Litigious', 'Constraining', 'Superfluous', 'Interesting', 'Modal']
    sent_dict = {}

    for col in sent_cols:
        sent_dict[col] = set([x.lower() for x in lm_panda[lm_panda[col] != 0]['Word'].tolist()])
    all_lists = data.Tokens.tolist()
    tokens_list = [val for sublist in all_lists for val in sublist]
    tokens_list = [val for sublist in tokens_list for val in sublist]

    # Creats the table with the idf scores
    idf_dict = idf(tokens_list)

    data.Tokens.head().apply(lambda note: lms(note, idf_dict, sent_dict, sent_cols))
    sent_col = [col for col in sent_cols]
    data[sent_col] = data.Tokens.apply(lambda note_tokens: pd.Series(lms(note_tokens, idf_dict, sent_dict, sent_cols)))
    data[sent_col].head()


if __name__ == '__main__':
    # analyse_from_excel()
    analyse_from_word('samples', 'input.csv')
