# Is it Raining?
A sophisticated application that mines twitter to determine whether it is currently raining in Austin, TX.

Web page: https://conorbarryhoke.github.io/is-it-raining/

## Overview
This repo contains all the code necessary for analyzing and exporting data from twitter to determine if it is currently raining. The output here is the isitraining.txt file, which gives a predicted probability of rain.  

This focus of this project is more about proof of concept for sharing information between platforms, running scripts on Google VMs, and creating ETL data pipelines. The model itself is secondary, and the output is meant to be taken <i>very</i> lightly.

The HTML required to deploy the infromation is <a href="https://github.com/conorbarryhoke/conorbarryhoke.github.io/tree/master/_posts">here</a> in the is-it-raining.md file. 

## Methodology
### Developing the Baseline (The Static Piece)
Notebook: <strong>scheduler_analysis.ipynb </strong> 
First, Twitter data (tweet text, time, and location) was mined for 5 active cities (including Austin) on days when it was and was not raining. This information was manually identified.  

Then, the contents of the tweets are analyzed and a logistic regression model is fit with the target value being is_rain. Essentially this is a binary classification problem: a 1 means that the tweet indicates it is currently raining, 0 means no rain at time of tweet. The assumption is that people tweet about different things when it rains.

Periodically, the model is manually updated to capture more combinations of weather and tweets and hopefully improve predictive capability.


### Script in Production (The Recurring Piece)
Notebook: <strong>scheduler.ipynb </strong> 
Script: <strong>scheduler.py </strong> 

The following steps are scripted in the py file to occur every 6 hours. The operations were developed in the ipython file with line-level documentation. 

1. Record Current Date and time
2. Log in to Twitter API and retrieve up to 700 tweets from the last day in Austin (Target city)
3. Save the data into a file for review in case of breakage
4. Transform the data with the saved transform from the static analysis, then predict probabilities that each tweet contains a text about rain.
5. Take the average of the predicted probabilities - this is interpreted as the overall probability that it is currently raining
6. Export time of call (update_date.txt) and rain probability (isitraining.txt) to separate text files on a Google Storage Bucket so that they can be shared publicly
7. Record time and prediction in update_log.csv for qc

The end result of this process is 2 text files which can then easily be read into a hosted site.
Note: For public files, Google Storage generally waits about an hour before updating the publicly facing information. 
## On the site side
On the github.io page, an object reads in the raining prediction and appends an interprative message. The time of update is separately recorded. 

Why do it this way? 
Hosting the application and website separately allows things like the Twitter API key used to remain private, as well as cutting down on transactions and therfore costs on the application server. 
A direct AJAX / JQUERY call would violate Same-Origin policy, so creating the public document seemed like a good work-around (and less intensive then developing an entire API to serve one number and one date at a time). 

# Fork / Clone / Copy notes
When replicating this implementation, note that the existing file structure is a <strong>must</strong>. The following files should be created before running all:
* 
