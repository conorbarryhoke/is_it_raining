import datetime, pandas as pd
import os, sys
import pytz
import pickle 
from importlib import import_module

# Custom Imports and scripts
cwd = os.getcwd()
sys.path.append(cwd)
import_module("my_bigq")

from my_bigq import bigquery_handler 

# standardize
def city_mapper(x):
    if x == 'Austin, TX':
        return 'Austin'
    if x == 'Seattle, WA':
        return 'Seattle'
    return 'other'

# Vectorizer
simple_cvec = pickle.load(open('../info/cvec_simple.sav', 'rb'))

with open("../cvec_feats.txt", "r") as f:
    good_feats = f.read()
    f.close()
good_feats = good_feats.split(', ')

lr = pickle.load(open('../new_log_reg_v2.sav', 'rb'))

def interpret_rain(probability):
    if probability > .8:
        return 'Its totally raining!'
    if probability > .5:
        return 'So Probably'
    if probability > .2:
        return 'Probably not raining'
    return 'Definitely not raining!'


f_path_full = "gs://twitter-weather/html-statements-public/isitraining.html"
f_path_date = "gs://twitter-weather/html-statements-public/update_date.html"

def run_main():
    # Load Data
    q_base_twitter = """
    SELECT * 
    FROM metridaticsmain.webscrapes.twitter_data_raw
    WHERE tweet_place = 'Austin, TX'
    """

    # https://googleapis.dev/python/bigquery/latest/usage/pandas.html
    df_twitter_r = bigquery_handler(q_base = q_base_twitter).run_query(how='selects')


    # De-dupe and downselect cities
    df_twitter_r = df_twitter_r.drop_duplicates(['tweet_time', 'tweet_text', 'tweet_place']).reset_index().drop('index', axis=1)
    df_twitter_r = df_twitter_r[df_twitter_r.tweet_place.isin(['Austin, TX', 'Seattle, WA'])].reset_index().drop('index', axis=1)


    df_twitter_r['hour_trunc'] = df_twitter_r.tweet_time.dt.floor('h')
    df_twitter_r['city_name'] = df_twitter_r['tweet_place'].apply(lambda x: city_mapper(x))

    print('Tweets Found: ', df_twitter_r.shape[0])

    # Analysis
    # Downselect to prevent too much vectorization
    tv_end = datetime.datetime.timestamp(df_twitter_r.tweet_time.max())
    tv_end = datetime.datetime.fromtimestamp(tv_end)

    tv_start = tv_end- datetime.timedelta(days=2)
    tv_start = tv_start.replace(tzinfo=pytz.utc)

    df_twitter_r = df_twitter_r[df_twitter_r.tweet_time>tv_start].reset_index().drop('index', axis=1)

    # load and transform twitter
    twitter_vectorized = simple_cvec.fit_transform(df_twitter_r.tweet_text)
    twitter_vectorized = pd.DataFrame(twitter_vectorized.toarray(), columns=simple_cvec.get_feature_names())
    twitter_vectorized = twitter_vectorized.loc[:, good_feats]
    twitter_vectorized['tweet_time'] = df_twitter_r['tweet_time']
    twitter_vectorized['is_Austin'] = (df_twitter_r['city_name'] == 'Austin')
    twitter_vectorized.set_index('tweet_time', inplace=True)

    twitter_vectorized = twitter_vectorized.loc[:, good_feats]

    # Create rolling
    tv_austin = twitter_vectorized

    # simple: From 25 until 2 hours ago
    tv_austin_1s = tv_austin.resample("1T").sum().fillna(0)
    tv_austin_25h = tv_austin_1s.rolling(window=25*60, min_periods=1).sum()
    tv_austin_2h = tv_austin_1s.rolling(window=2*60, min_periods=1).sum()

    tv_austin_diff = tv_austin_25h - tv_austin_2h
    tv_austin_diff['hour_trunc'] = pd.Series(tv_austin_diff.index, index=tv_austin_diff.index).dt.floor('h')

    # load model, predict, get probas
    X = tv_austin_diff.loc[:, good_feats]

    preds = lr.predict(X)
    probas = lr.predict_proba(X)
    probas = [element[1] for element in probas]

    most_recent_proba = probas[-1]

    # Prediction for time
    most_recent_time = tv_austin_diff.index.max()
    most_recent_time = most_recent_time.replace(tzinfo=pytz.utc)
    most_recent_time = most_recent_time.astimezone(pytz.timezone('America/Chicago'))

    # Statement
    _rain_probability = '{:.1%}'.format(most_recent_proba)
    rain_qualifier = interpret_rain(most_recent_proba)

    html_statement = '<!DOCTYPE html><html><head><style type="text/css">.karen_message{}</style><style type="text/css">.qualifier_message{} </style></head><body><center><p class="karen_message">This is Karen_Bot with the weather! <br><br>I am here in Austin and there is a <br><strong>{}</strong> chance that it is already raining! <br><br><i class="qualifier_message">{}</i> </p></center> </body></html>'.format("{font-size: 16px};","{font-size: 12px};", _rain_probability, rain_qualifier)

    f= open("../isitraining.html","w+")
    f.write(html_statement)
    f.close() 

    f= open("../update_date.txt","w+")
    f.write('{:%B %d, %Y at %H:%M} CST'.format(most_recent_time,most_recent_time ))
    f.close() 

    # copy in new
    rez1 = os.system("gsutil cp -r {}/../isitraining.html {}".format(cwd, f_path_full))
    rez2 = os.system("gsutil cp -r {}/../update_date.txt {}".format(cwd, f_path_date))

    # set access public
    rez3 = os.system("gsutil acl ch -u AllUsers:R {}".format(f_path_full))
    rez4 = os.system("gsutil acl ch -u AllUsers:R {}".format(f_path_date))
    return [rez1, rez2, rez3, rez4]

if __name__ == "__main__":
    rez1, rez2, rez3, rez4 = run_main()
    print(datetime.datetime.now())
    print(rez1, rez2, rez3, rez4)
