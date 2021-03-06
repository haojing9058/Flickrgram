"""For cleaning and structuring data."""

import pandas as pd
import nltk
from nltk.corpus import stopwords
from string import punctuation
from sqlalchemy import create_engine
from string import punctuation
from collections import Counter
from model import User, Photo
from model import connect_to_db, db

UNWANTED_WORDS = set(stopwords.words('english')).union(set(['facebook', 'instagram', 'thanks', 'follow', 'share', 'a7rm2',
            'please', 'page', 'visit', 'thanks', 'feel', 'like', 'ig', 'image', 'also', 'I', 'l', 'na', 'ba', 'ive', 'b', 'bplease', 'quotfquot', 'hessen', 'loch']))


def strip_punctuation (str):
    """Replace punctuation with empty space."""
    if not str:
        return str
    else:
        for p in list(punctuation):
            str = str.lower().replace(p, '')
    return str


def users_word_count(username1, username2, text_type='tags'):
    """Return certain text_type of word counts for each user and their common word counts"""

    def count_word(username, text_type='tags'):
        """Return certain text_type of word counts dataframe for a given user.
        (string1, string2) --> dataframe
        text_type: options of "tags", title", "description". Defalt to "tags".
        """

        #get a list of tutples of srtings
        if text_type == 'tags':
            raw_data = db.session.query(Photo.tags).filter(Photo.username == username).all()
        elif text_type == 'title':
            raw_data = db.session.query(Photo.title).filter(Photo.username == username).all()
        elif text_type == 'description':
            raw_data = db.session.query(Photo.description).filter(Photo.username == username).all()

        #get a list of strings
        str_lst = [e for l in raw_data for e in l]

        #lower case and strip punctuations of a string
        str_lst_new = map(strip_punctuation, str_lst)

        word_lst = [w for sentence in str_lst_new if sentence for w in sentence.split()]
        if word_lst:

            #remove stop words
            filtered_words = [w for w in word_lst if not w in UNWANTED_WORDS]

            #get word count dictionary
            counts = Counter(filtered_words)

            #convert dict to dataframe
            df = pd.DataFrame.from_dict(counts, orient='index').reset_index()

            #add "user" column to the dataframe
            df['user'] = pd.Series(username, index=df.index)

            #rename columns
            df.rename(columns={'index':'word', 0:'count', 'user':'user'}, inplace=True)

            #drop rows if word length is over 15
            df = df[df['word'].apply(lambda x: len(x) < 15)]
            
            #sort and select top 20
            df_new = df.sort_values(by='count',ascending = False).head(20)

            return df_new

        else:
            empty_df = pd.DataFrame(columns=['word', 'count', 'user'])
            empty_df['user'] = pd.Series(username)

            return empty_df

    #word counts for each user
    words1 = count_word(username1, text_type)
    words2 = count_word(username2, text_type)

    #common word and sum of counts
    common = words1.merge(words2, how='inner', on='word')
    common['count'] = common['count_x'] + common['count_y']
    common['user'] = 'common'
    common = common[['word', 'count', 'user']]

    #word counts by user 1 only
    words1 = words1.merge(words2, how='left', on='word')
    words1 = words1[words1['count_y'].isnull()].drop(['count_y', 'user_y'], axis=1)
    words1.columns = ['word','count','user']

    #word counts by user 2 only
    words2 = words2.merge(common, how='left', on='word')
    words2 = words2[words2['count_y'].isnull()].drop(['count_y', 'user_y'], axis=1)
    words2.columns = ['word','count','user']

    #concatenat the common, user 1 only, and user 2 only
    df = pd.concat([words1, words2, common])

    return df


def get_tags_csv(df):
    """Save tags dataframe to .csv"""
    return df.to_csv(path_or_buf=r'static/tags.csv', header=False, index=False, encoding='utf-8')


def get_title_csv(df):
    """Save title dataframe to .csv"""
    return df.to_csv(path_or_buf=r'static/title.csv', header=False, index=False, encoding='utf-8')


def get_description_csv(df):
    """Save title dataframe to .csv"""
    return df.to_csv(path_or_buf=r'static/description.csv', header=False, index=False, encoding='utf-8')


def get_match_score(df):
    """ Calculate match score given the "word, count, user" df.
    """
    sum_of_common = df.loc[df['user']=='common', 'count'].sum()
    total = df['count'].sum()
    if total:
        match_score = float(sum_of_common) / float(total)
        return '{0:.2f}%'.format(match_score*100)
    else: 
        return '0.00%'


def get_tag_lst():
    """Return a list of tags used by both users.
    If no common tags, return the top 5 by count. 
    """
    df = pd.read_csv('static/tags.csv', header=None, names=['word', 'count', 'user'])
    df_common = df[df['user'] == 'common']

    if df_common['count'].isnull().sum() == 0:
        df_top = df.sort_values(by= 'count', ascending=False).head(5)
        tag_lst = df_top['word'].tolist()
    else:
        tag_lst = df_common['word'].tolist()

    return tag_lst


def get_text_lst():
    """
    Return a list of words used by both users used in title or description.
    If no common words, return the top 5 by count.
    """
    df_title = pd.read_csv('static/title.csv', header=None, names=['word', 'count', 'user'])
    df_description = pd.read_csv('static/description.csv', header=None, names=['word', 'count', 'user'])
    df = pd.concat([df_title, df_description])
    df_common = df[df['user'] == 'common']

    if df_common['count'].isnull().sum() == 0:
        df_top = df.sort_values(by= 'count', ascending=False).head(5)
        text_lst = df_top['word'].tolist()
    else:
        text_lst = df_common['word'].tolist()

    return text_lst


# globle variables for geo function.
COUNTRY_CODE = pd.read_csv('static/countries_code.csv')
COUNTRY_CODE.index = COUNTRY_CODE['country']
TEMPLATE_DF = pd.DataFrame(columns=['latitude', 'longitude', 2010, 2011, 2012, 2013, 
    2014, 2015, 2016, 2017, 2018, 'country_name', 'user'])
TEMPLATE_DF.index.name = 'country_code'


def geo(username):
    #get a list of tuples
    raw_data = db.session.query(Photo.photo_id, Photo.country_code, Photo.date_taken).filter(Photo.username == username).all()
    #convert raw_data to dataframe
    df = pd.DataFrame.from_records(raw_data, columns=['photo_id', 'country_code', 'date_taken'])
    #drop rows with missing values
    df.dropna(inplace=True)
    #check if df is empty
    if df.count == 0:
        return TEMPLATE_DF
    #extrat year and save as a new column
    df['year'] = df['date_taken'].map(lambda x: x.year)
    #select photos taken in or after 2010.
    df = df[df['year'] >= 2010]
    #group by country_code, year
    group = df.groupby(by=['country_code', 'year']).size()
    df_group = group.reset_index()
    df_group.columns = ['country_code', 'year', 'count']
    #year column to year rows
    records_df = df_group.pivot_table('count', 'country_code', 'year')
    #merge with TEMPLATE_DF
    merged = records_df.merge(COUNTRY_CODE, left_index=True, right_index=True, how='left')
    #get user column
    merged['user'] = pd.Series(username, index=merged.index)
    # concat with TEMPLATE_DF in order to have columns of all years in range
    concat = merged.merge(TEMPLATE_DF, how='outer')
    # resorder column based on column names
    result = concat.reindex(sorted(concat.columns), axis=1)
    #replace NaN with 0
    result.fillna(value=0, inplace=True)
    return result


def get_geo_csv(df1, df2):
    """save two dataframes into "geo.csv" """
    new = pd.concat([df1, df2], ignore_index=True)
    return new.to_csv(path_or_buf='static/geo.csv', encoding='utf-8')


def get_lat_lon():
    """Return the lat-lon lists of the countries the both users have visited,
    or each individual user's top visited country."""
    df = pd.read_csv('static/geo.csv')
    df['total'] = df['2010'] + df['2011'] + df['2012'] + df['2013'] + df['2014'] + df['2015'] + df['2016'] + df['2017'] + df['2018']

    if len(set(df['user'])) == 2:

        user1, user2 = set(df['user'])
        set1 = set(df.loc[df['user']==user1]['country_name'])
        set2 = set(df.loc[df['user']==user2]['country_name'])
        common = set1 & set2
        if common:
            geo_array = df.loc[df['country_name'].isin(common)].sort_values(by=['country_name','total'], 
                ascending=False).drop_duplicates(subset=['latitude', 'longitude'], 
                keep='first').sort_values(by=['total'], ascending=False).head(2)[['latitude','longitude']].values.tolist()
            return geo_array

        else:
            top_geo1 = df.loc[df['user']==user1].sort_values(by='total', ascending=False).head(1)[['latitude',  'longitude']]
            top_geo2 = df.loc[df['user']==user2].sort_values(by='total', ascending=False).head(1)[['latitude',  'longitude']]
            return top_geo1.values.tolist() + top_geo2.values.tolist()

    elif len(set(df['user'])) == 1:
        top_geo = df.sort_values(by='total', ascending=False).head(2)[['latitude', 'longitude']]
        return top_geo.values.tolist()


if __name__ == "__main__":
    from flask import Flask, request, session
    from model import connect_to_db, db
    app = Flask(__name__)
    connect_to_db(app)
