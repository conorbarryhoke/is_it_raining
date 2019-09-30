import os, sys
cwd = os.getcwd()
sys.path.append(cwd)
from importlib import import_module
import_module("my_bigq")
from my_bigq import bigquery_handler

import datetime, tweepy
import pandas as pd
from numpy import floor
from time import sleep


def clean_chars(val_string):
    val_string = val_string.replace("'", "")
    val_string = val_string.replace("\\", "")

    return val_string

def combine_tweet_info(tweet_text, tweet_time, tweet_place):
    tweet_text = clean_chars(tweet_text)

    return "('" + tweet_place + "', '" + str(tweet_time) + "', '" + tweet_text + "') "

def define_api():
    with open('../info/twitterapi2.txt') as f:
        ck, cs, atk, ats = f.read().split(',')

    twitter_keys = {
    'consumer_key':        ck.replace('\n', ''),
    'consumer_secret':     cs.replace('\n', ''),
    'access_token_key':    atk.replace('\n', ''),
    'access_token_secret': ats.replace('\n', '')
    }

    auth = tweepy.OAuthHandler(twitter_keys['consumer_key'], twitter_keys['consumer_secret'])
    auth.set_access_token(twitter_keys['access_token_key'], twitter_keys['access_token_secret'])
    api = tweepy.API(auth, wait_on_rate_limit=True,wait_on_rate_limit_notify=True)

    return api


def get_twitter(api, place_q):


    time_now = datetime.datetime.now()
    time_start = datetime.datetime.now() - datetime.timedelta(days=1)
    time_stop = datetime.datetime.now() + datetime.timedelta(days=1)
    start_date = '{}-{}-{}'.format(time_start.year, time_start.month, time_start.day)
    end_date = '{}-{}-{}'.format(time_stop.year, time_stop.month, time_stop.day)

    df_big = pd.DataFrame()

    tweetsPerQry = 100
    counter = 0

    place = api.geo_search(query=place_q, granularity="city")
    place_id = place[0].id

    max_id = -1
    for _ in range(20):
        try:
            if (max_id <= 0):
                new_tweets = api.search(q='place:%s' % place_id, count=tweetsPerQry, since=start_date, until=end_date)
            else:
                new_tweets = api.search(q='place:%s' % place_id, count=tweetsPerQry, max_id=str(max_id - 1), since=start_date, until=end_date)

            df_text = pd.DataFrame([new_tweets[i]._json['text'] for i in range(len(new_tweets))], columns=['tweet_text'])
            df_text['tweet_time']=[new_tweets[i]._json['created_at'] for i in range(len(new_tweets))]
            df_text['tweet_place'] = place_q

            df_big = pd.concat([df_big, df_text])

            if not new_tweets:
                counter += 1
                print("No more tweets found")
                break

            max_id = new_tweets[-1].id
        except tweepy.TweepError as e:
            print('    all_done')
            break
        sleep(5)

    df_big['tweet_time'] = pd.to_datetime(df_big.tweet_time)

    return df_big

def process_twitter(df_big):
    num_rows = df_big.shape[0]
    # this will be a list of lists, converted to list of strings
    values_combined = []

    if num_rows <= 500:
        values_combined = [df_big.apply(lambda x: combine_tweet_info(x['tweet_text'], x['tweet_time'], x['tweet_place'] ), axis=1).values]
    else:
        n_chunks = int(floor(num_rows/500))
        print('found {} chunks'.format(n_chunks))

        for n in range(n_chunks):
            _rel = df_big.iloc[n*500: (n+1)*500, :]
            if _rel.shape[0] == 0: # cases where df_big is a multiple of 1000
                continue
            _rel_combined = _rel.apply(lambda x: combine_tweet_info(x['tweet_text'], x['tweet_time'], x['tweet_place'] ), axis=1).values
            values_combined.append(_rel_combined)

    for i in range(len(values_combined)):
        values_combined[i] = ', '.join(values_combined[i])


    return values_combined

def send_to_table(values_combined):
    rez_list = []
    for subset in values_combined:
        q_base = """
            INSERT INTO metridaticsmain.webscrapes.twitter_data_raw (
             tweet_place,  tweet_time, tweet_text
            )
            VALUES {}
            ;
            """.format(subset)

        q_base = q_base.replace("\n", "")

        rez = bigquery_handler(q_base=q_base).run_query()
        rez_list.append(rez)

    return rez_list

def run_city(city):
    api = define_api()
    df_big = get_twitter(api, city)
    values_combined = process_twitter(df_big)
    send_to_table(values_combined)

def run_main():
    run_city("Austin, TX")
    run_city("Seattle, WA")

if __name__ == "__main__":
    run_main()

