# Imports
from time import sleep
import twitter, re, datetime, pandas as pd
import sys
import re
import time
import tweepy
import os
import pickle
from sklearn.linear_model import LogisticRegression

#Load Models
cvec = pickle.load(open('vectorizer.sav', 'rb'))
lr = pickle.load(open('lin_regressor.sav', 'rb'))

#Load twitter api keys
with open('./twitterapi.txt') as f:
    ck, cs, atk, ats = f.read().split(',')
twitter_keys = {
    'consumer_key':        ck,
    'consumer_secret':     cs,
    'access_token_key':    atk,
    'access_token_secret': ats
}
auth = tweepy.OAuthHandler(twitter_keys['consumer_key'], twitter_keys['consumer_secret'])
auth.set_access_token(twitter_keys['access_token_key'], twitter_keys['access_token_secret'])
api = tweepy.API(auth, wait_on_rate_limit=True,wait_on_rate_limit_notify=True)
# Define hour convention for text - datetime is GMT - 6, so we have to update it for CST
def hour_converter(_time_input):
    _time_zone_adjustment = 6
    if _time_input < _time_zone_adjustment:
        _hour_statement = str(_time_input - _time_zone_adjustment + 24) + ":00 PM"
    elif _time_input == _time_zone_adjustment:
        _hour_statement = "12:00 AM"
    elif _time_input < 19:
        _hour_statement = str(_time_input - _time_zone_adjustment) + ":00 AM"
    else:
        _hour_statement = str(_time_input - _time_zone_adjustment) + ":00 PM"
    return _hour_statement

update_interval_hours = 3
for i in range(7*2*int(24/update_interval_hours)): # Should run for about 2 weeks
    # Beginning of things actually in the loop
    tomorrow = datetime.datetime.now() + datetime.timedelta(1)
    today = datetime.datetime.now()
    yesterday = datetime.datetime.now() - datetime.timedelta(1)
    # Variables formatted for tweepy paramaters
    end_date = '{}-{}-{}'.format(tomorrow.year, tomorrow.month, tomorrow.day)
    start_date = '{}-{}-{}'.format(yesterday.year, yesterday.month, yesterday.day)

    # Configuring API query, giving data a place to land
    df_small = pd.DataFrame()
    places = ["Austin, TX"]
    tweetsPerQry = 100
    counter = 0

    for place_q in places:

        place = api.geo_search(query=place_q, granularity="city")
        place_id = place[0].id

        max_id = -1
        for _ in range(10):
            try:
                if (max_id <= 0):
                    new_tweets = api.search(q='place:%s' % place_id, count=tweetsPerQry, since=start_date, until=end_date)
                else:
                    new_tweets = api.search(q='place:%s' % place_id, count=tweetsPerQry, max_id=str(max_id - 1), since=start_date, until=end_date)

                df_text = pd.DataFrame([new_tweets[i]._json['text'] for i in range(len(new_tweets))], columns=['tweet_text'])
                df_text['tweet_time']=[new_tweets[i]._json['created_at'] for i in range(len(new_tweets))]
                df_text['tweet_place'] = place_q

                df_small = pd.concat([df_small, df_text])

                if not new_tweets:
                    counter += 1
                    df_small.to_csv('./data/collected_tweets_{}.csv'.format(counter)) # Should provide log of last good pull at least

                    print("No more tweets found")
                    break

                max_id = new_tweets[-1].id
            except tweepy.TweepError as e:
                print('    all_done')
                break
            sleep(5) # Avoid overloading the system
    # Try to use only the most recent tweets
    # If there are not enough, use a wider range
    df_small["tweet_time"] = pd.to_datetime(df_small.tweet_time)
    if df_small[df_small.tweet_time > (datetime.datetime.now() - datetime.timedelta(hours=2))].shape[0] > 50:
        df_small = df_small[df_small.tweet_time > (datetime.datetime.now() - datetime.timedelta(hours=2))]
    elif df_small[df_small.tweet_time > (datetime.datetime.now() - datetime.timedelta(hours=4))].shape[0]>50:
        df_small = df_small[df_small.tweet_time > (datetime.datetime.now() - datetime.timedelta(hours=4))]
    else:
        df_small = df_small
    # Transform twitter data to match model features. Method will fill in empty columns
    model_columns = cvec.get_feature_names()
    df_small = pd.concat([df_small.reset_index().drop('index', axis=1), pd.DataFrame(cvec.transform(df_small.tweet_text.str.lower()).todense(), columns=cvec.get_feature_names())], axis=1)
    _X = df_small.loc[:, [col for col in df_small.columns if col in model_columns]]
    _X.fillna(0, inplace=True)

    df_small['predicted'] = lr.predict(_X)
    df_small['probas'] = [element[1] for element in lr.predict_proba(_X)]
    # Average predicted probability rain is assumed to be probability of current rain
    excludes = ['tweet_text', 'tweet_time', 'tweet_place', 'is_rain', 'predicted']
    _rain_probability = df_small.loc[:, excludes + ['predicted', 'probas']].groupby('tweet_place').mean()['probas'].values[0]
    _rain_probability = round(_rain_probability*100, 1)
    # Write in an interpretation statement to improve UX
    if _rain_probability < 20:
        rain_qualifier = "(so probably not)"
    elif _rain_probability < 40:
        rain_qualifier = "(so maybe?)"
    elif _rain_probability < 80:
        rain_qualifier = "(so probably!)"
    else:
        rain_qualifier = "Its definitely raining!"

    html_statement = '<!DOCTYPE html><html><head><style type="text/css">.karen_message{}</style><style type="text/css">.qualifier_message{} </style></head><body><center><p class="karen_message">This is Karen_Bot with the weather! <br><br>I am here in Austin and there is a <br><strong>{}%</strong> chance that it is already raining! <br><br><i class="qualifier_message">{}</i> </p></center> </body></html>'.format("font-size: 16px;","font-size: 12px;", _rain_probability, rain_qualifier)


    # Edit raining file to read as current rain probability
    f= open("isitraining.html","w+")
    f.write(html_statement)
    f.close()
    # Edit update date file to read as date at time of Twitter call
    f= open("update_date.txt","w+")
    f.write('{} {}, {} at {}'.format(datetime.datetime.now().strftime("%B"), today.day,today.year, hour_converter(today.hour)))
    f.close()
    # copy in new (command is specific to Google VM)
    os.system("gsutil cp -r ~/isitraining.html gs://is-it-raining/")
    os.system("gsutil cp -r ~/update_date.txt gs://is-it-raining/")
    # set access public (command is specific to Google VM)
    os.system("gsutil acl ch -u AllUsers:R gs://is-it-raining/isitraining.html")
    os.system("gsutil acl ch -u AllUsers:R gs://is-it-raining/update_date.txt")
    # Update the log to record date, time, and prediction
    update_log = pd.read_csv('./update_log.csv')
    update_log = pd.concat([update_log, pd.DataFrame({'Date': datetime.datetime.now(), 'rain_statement': _rain_probability}, index=[0])])
    update_log.to_csv('./update_log.csv', index=False)

    sleep(update_interval_hours*60*60)
